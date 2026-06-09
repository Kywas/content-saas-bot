from __future__ import annotations

import random
from enum import StrEnum

from openai import AsyncOpenAI

from app.config import Settings


class ContentType(StrEnum):
    POST = "post"
    HOOKS = "hooks"
    PLAN = "plan"
    CAPTION = "caption"


HOOK_TEMPLATES = [
    "Почему 90% {niche} терпят неудачу — и как попасть в 10%",
    "3 ошибки в {niche}, которые стоят вам клиентов каждый месяц",
    "Я потратил 6 месяцев на {niche}. Вот что реально работает",
    "Никто не говорит об этом в {niche}. А зря",
    "Один простой шаг в {niche}, который удвоил мои результаты",
]

POST_STRUCTURES = [
    (
        "🔥 {hook}\n\n"
        "Большинство думает, что в {niche} главное — {myth}.\n"
        "На деле работает другое: {truth}.\n\n"
        "Что делать прямо сейчас:\n"
        "1) {step1}\n"
        "2) {step2}\n"
        "3) {step3}\n\n"
        "Сохрани, чтобы не потерять."
    ),
    (
        "Если ты в нише «{niche}», прочитай это.\n\n"
        "❌ Не делай: {dont}\n"
        "✅ Делай: {do}\n\n"
        "Почему? {reason}\n\n"
        "Попробуй сегодня и напиши, что изменилось."
    ),
]

PLAN_DAYS = [
    "Пост-история: личный кейс в нише",
    "Карусель: 5 ошибок новичков",
    "Reels/Shorts: быстрый лайфхак",
    "Пост-опрос: вовлечение аудитории",
    "Разбор тренда в нише",
    "Пост с чек-листом",
    "Итоги недели + призыв к действию",
]

MYTHS = [
    "больше постов",
    "дорогая реклама",
    "идеальный визуал",
    "копирование конкурентов",
]
TRUTHS = [
    "регулярность и ясное позиционирование",
    "сильный оффер и доверие",
    "понятная польза в каждом посте",
    "свой голос и конкретные кейсы",
]
STEPS = [
    "определи одну боль аудитории",
    "напиши пост с конкретным решением",
    "добавь призыв: комментарий или сохранение",
    "собери 10 идей в заметки",
    "сними 30-секундное видео",
    "ответь на 5 комментариев под чужими постами",
]


def _pick(items: list[str]) -> str:
    return random.choice(items)


def _generate_offline(content_type: ContentType, niche: str) -> str:
    if content_type == ContentType.HOOKS:
        hooks = [_pick(HOOK_TEMPLATES).format(niche=niche) for _ in range(5)]
        return "🪝 5 хуков для твоего контента:\n\n" + "\n\n".join(
            f"{i}. {h}" for i, h in enumerate(hooks, 1)
        )

    if content_type == ContentType.PLAN:
        lines = [f"День {i + 1}: {task}" for i, task in enumerate(PLAN_DAYS)]
        return (
            f"📅 Контент-план на 7 дней для ниши «{niche}»:\n\n"
            + "\n".join(lines)
            + "\n\n💡 Публикуй в одно время — так алгоритм быстрее запомнит тебя."
        )

    if content_type == ContentType.CAPTION:
        return (
            f"✍️ Подпись для поста в нише «{niche}»:\n\n"
            f"{_pick(HOOK_TEMPLATES).format(niche=niche)}\n\n"
            f"Сегодня разобрал, как {_pick(STEPS).lower()} — и это реально сдвинуло дело.\n\n"
            f"А у тебя какой главный затык в {niche}? Пиши в комментариях 👇\n\n"
            f"#{niche.replace(' ', '')} #контент #бизнес"
        )

    hook = _pick(HOOK_TEMPLATES).format(niche=niche)
    template = _pick(POST_STRUCTURES)
    return template.format(
        hook=hook,
        niche=niche,
        myth=_pick(MYTHS),
        truth=_pick(TRUTHS),
        step1=_pick(STEPS),
        step2=_pick(STEPS),
        step3=_pick(STEPS),
        dont=_pick(MYTHS),
        do=_pick(TRUTHS),
        reason=_pick(TRUTHS),
    )


async def generate_content(
    settings: Settings,
    content_type: ContentType,
    niche: str,
    extra: str | None = None,
) -> str:
    niche = niche.strip() or "бизнес"
    if not settings.openai_api_key:
        return _generate_offline(content_type, niche)

    prompts = {
        ContentType.POST: (
            f"Напиши готовый пост для соцсетей в нише «{niche}». "
            f"Стиль: живой, без воды, с призывом к действию. "
            f"Дополнительно: {extra or 'без уточнений'}."
        ),
        ContentType.HOOKS: (
            f"Дай 5 цепляющих хуков для контента в нише «{niche}». "
            f"Каждый с новой строки, пронумерованный."
        ),
        ContentType.PLAN: (
            f"Составь контент-план на 7 дней для ниши «{niche}». "
            f"Каждый день — конкретная тема и формат."
        ),
        ContentType.CAPTION: (
            f"Напиши подпись к посту в нише «{niche}» с хештегами. "
            f"Дополнительно: {extra or 'без уточнений'}."
        ),
    }

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты копирайтер для соцсетей. Пиши на русском, кратко и по делу. "
                    "Без markdown-заголовков."
                ),
            },
            {"role": "user", "content": prompts[content_type]},
        ],
        temperature=0.9,
        max_tokens=900,
    )
    text = (response.choices[0].message.content or "").strip()
    return text or _generate_offline(content_type, niche)
