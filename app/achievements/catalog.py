from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

AchievementTrigger = Literal[
    "message_created",
    "reply_created",
    "media_created",
    "reaction_received",
    "streak_updated",
    "level_changed",
    "ranking_calculated",
    "weekly_report_created",
]
AchievementScope = Literal["group", "global"]
AchievementComparator = Literal["gte", "lte"]


class AchievementRarity(StrEnum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    SECRET = "secret"


RARITY_THEME: dict[AchievementRarity, str] = {
    AchievementRarity.COMMON: "blue_pulse",
    AchievementRarity.UNCOMMON: "green_particles",
    AchievementRarity.RARE: "purple_wave",
    AchievementRarity.EPIC: "epic_flare",
    AchievementRarity.LEGENDARY: "golden_rays",
    AchievementRarity.SECRET: "secret_glitch",
}


@dataclass(frozen=True, slots=True)
class AchievementDefinition:
    code: str
    title: str
    description: str
    category: str
    rarity: AchievementRarity
    scope: AchievementScope
    icon: str
    visual_theme: str
    hidden: bool
    chain_key: str | None
    chain_stage: int
    chain_total: int
    trigger: AchievementTrigger
    metric: str
    threshold: int
    comparator: AchievementComparator = "gte"
    important: bool = False
    reward_xp: int = 0
    version: int = 2
    season_key: str | None = None

    def to_public_dict(
        self,
        *,
        earned: bool,
        progress: int,
        earned_at: str | None = None,
        group_title: str | None = None,
    ) -> dict[str, Any]:
        locked_secret = self.hidden and not earned
        return {
            "code": self.code,
            "title": "???" if locked_secret else self.title,
            "description": "Секретне досягнення" if locked_secret else self.description,
            "category": self.category,
            "rarity": self.rarity.value,
            "scope": self.scope,
            "icon": "sparkles" if locked_secret else self.icon,
            "visual_theme": "secret_locked" if locked_secret else self.visual_theme,
            "hidden": self.hidden,
            "important": self.important,
            "earned": earned,
            "earned_at": earned_at,
            "group_title": group_title,
            "progress": 0 if locked_secret else min(max(progress, 0), self.threshold),
            "threshold": 0 if locked_secret else self.threshold,
            "chain": (
                {
                    "key": self.chain_key,
                    "stage": self.chain_stage,
                    "total": self.chain_total,
                }
                if self.chain_key is not None
                else None
            ),
            "reward_xp": self.reward_xp,
            "version": self.version,
            "season_key": self.season_key,
        }


def _rarity_for_stage(stage: int, total: int) -> AchievementRarity:
    ratio = stage / max(total, 1)
    if ratio >= 1:
        return AchievementRarity.LEGENDARY
    if ratio >= 0.8:
        return AchievementRarity.EPIC
    if ratio >= 0.55:
        return AchievementRarity.RARE
    if ratio >= 0.3:
        return AchievementRarity.UNCOMMON
    return AchievementRarity.COMMON


def _chain(
    *,
    key: str,
    category: str,
    trigger: AchievementTrigger,
    metric: str,
    scope: AchievementScope,
    icon: str,
    stages: tuple[tuple[str, str, str, int], ...],
) -> tuple[AchievementDefinition, ...]:
    total = len(stages)
    return tuple(
        AchievementDefinition(
            code=code,
            title=title,
            description=description,
            category=category,
            rarity=_rarity_for_stage(index, total),
            scope=scope,
            icon=icon,
            visual_theme=RARITY_THEME[_rarity_for_stage(index, total)],
            hidden=False,
            chain_key=key,
            chain_stage=index,
            chain_total=total,
            trigger=trigger,
            metric=metric,
            threshold=threshold,
            important=index >= max(2, total - 1),
            reward_xp=index * 5,
        )
        for index, (code, title, description, threshold) in enumerate(stages, start=1)
    )


MESSAGE_CHAIN = _chain(
    key="messages",
    category="activity",
    trigger="message_created",
    metric="messages_count",
    scope="group",
    icon="message-circle",
    stages=(
        ("messages_10", "Перше слово", "Надіслано 10 повідомлень", 10),
        ("messages_100", "Перша сотня", "Надіслано 100 повідомлень", 100),
        ("messages_500", "Розговорився", "Надіслано 500 повідомлень", 500),
        ("messages_1000", "Машина спілкування", "Надіслано 1 000 повідомлень", 1_000),
        ("messages_2500", "Голос групи", "Надіслано 2 500 повідомлень", 2_500),
        ("messages_5000", "Невтомний співрозмовник", "Надіслано 5 000 повідомлень", 5_000),
        ("messages_10000", "Легенда чату", "Надіслано 10 000 повідомлень", 10_000),
        ("messages_25000", "Серце спільноти", "Надіслано 25 000 повідомлень", 25_000),
    ),
)

REPLY_CHAIN = _chain(
    key="replies",
    category="dialogue",
    trigger="reply_created",
    metric="replies_count",
    scope="group",
    icon="reply",
    stages=(
        ("replies_10", "У діалозі", "Надіслано 10 відповідей", 10),
        ("replies_50", "Підтримав розмову", "Надіслано 50 відповідей", 50),
        ("replies_100", "Майстер діалогу", "Надіслано 100 відповідей", 100),
        ("replies_250", "Завжди на зв’язку", "Надіслано 250 відповідей", 250),
        ("replies_500", "Діалоговий двигун", "Надіслано 500 відповідей", 500),
        ("replies_1000", "Той, хто відповідає", "Надіслано 1 000 відповідей", 1_000),
        ("replies_2500", "Архітектор розмов", "Надіслано 2 500 відповідей", 2_500),
    ),
)

REACTION_CHAIN = _chain(
    key="reactions",
    category="reactions",
    trigger="reaction_received",
    metric="reactions_received",
    scope="group",
    icon="heart",
    stages=(
        ("reactions_1", "Перша реакція", "Отримано першу реакцію", 1),
        ("reactions_10", "Помітили", "Отримано 10 реакцій", 10),
        ("reactions_50", "Подобається людям", "Отримано 50 реакцій", 50),
        ("reactions_100", "Улюбленець групи", "Отримано 100 реакцій", 100),
        ("reactions_250", "Магніт реакцій", "Отримано 250 реакцій", 250),
        ("reactions_500", "Емоційний центр", "Отримано 500 реакцій", 500),
        ("reactions_1000", "Тисяча емоцій", "Отримано 1 000 реакцій", 1_000),
        ("reactions_2000", "Ікона групи", "Отримано 2 000 реакцій", 2_000),
    ),
)

PHOTO_CHAIN = _chain(
    key="photos",
    category="media",
    trigger="media_created",
    metric="photo_count",
    scope="group",
    icon="image",
    stages=(
        ("photos_1", "Перший кадр", "Надіслано перше фото", 1),
        ("photos_10", "Фотоальбом", "Надіслано 10 фото", 10),
        ("photos_50", "Папараці", "Надіслано 50 фото", 50),
        ("photos_100", "Хронікер групи", "Надіслано 100 фото", 100),
        ("photos_250", "Візуальна історія", "Надіслано 250 фото", 250),
        ("photos_500", "Фотолегенда", "Надіслано 500 фото", 500),
        ("photos_1000", "Тисяча моментів", "Надіслано 1 000 фото", 1_000),
    ),
)

VOICE_CHAIN = _chain(
    key="voices",
    category="media",
    trigger="media_created",
    metric="voice_count",
    scope="group",
    icon="mic",
    stages=(
        ("voices_1", "Перший голос", "Надіслано перше голосове", 1),
        ("voices_10", "Говорить ChatPulse", "Надіслано 10 голосових", 10),
        ("voices_25", "Голос чату", "Надіслано 25 голосових", 25),
        ("voices_50", "Ефір триває", "Надіслано 50 голосових", 50),
        ("voices_100", "Радіоведучий", "Надіслано 100 голосових", 100),
        ("voices_250", "Подкастер групи", "Надіслано 250 голосових", 250),
        ("voices_500", "Легендарний голос", "Надіслано 500 голосових", 500),
    ),
)

GROUP_XP_CHAIN = _chain(
    key="group_xp",
    category="activity",
    trigger="message_created",
    metric="xp_total",
    scope="group",
    icon="zap",
    stages=(
        ("first_steps", "Перші кроки", "Набрано 10 XP у групі", 10),
        ("xp_100", "Пульс запущено", "Набрано 100 XP у групі", 100),
        ("xp_500", "Стабільний ритм", "Набрано 500 XP у групі", 500),
        ("xp_1000", "Тисяча енергії", "Набрано 1 000 XP у групі", 1_000),
        ("xp_5000", "Висока напруга", "Набрано 5 000 XP у групі", 5_000),
        ("xp_10000", "Енергетичне ядро", "Набрано 10 000 XP у групі", 10_000),
        ("xp_25000", "Невгасимий пульс", "Набрано 25 000 XP у групі", 25_000),
        ("xp_50000", "Абсолютний резонанс", "Набрано 50 000 XP у групі", 50_000),
    ),
)

STREAK_CHAIN = _chain(
    key="streak",
    category="streak",
    trigger="streak_updated",
    metric="current_streak",
    scope="group",
    icon="flame",
    stages=(
        ("streak_3", "Розігрів", "Серія активності 3 дні", 3),
        ("streak_7", "Тиждень у ритмі", "Серія активності 7 днів", 7),
        ("streak_14", "Два тижні разом", "Серія активності 14 днів", 14),
        ("streak_30", "Місяць без пауз", "Серія активності 30 днів", 30),
        ("streak_60", "Залізна звичка", "Серія активності 60 днів", 60),
        ("streak_100", "Сто днів пульсу", "Серія активності 100 днів", 100),
        ("streak_180", "Пів року в ритмі", "Серія активності 180 днів", 180),
        ("streak_365", "Рік без тиші", "Серія активності 365 днів", 365),
    ),
)

LEVEL_CHAIN = _chain(
    key="levels",
    category="levels",
    trigger="level_changed",
    metric="level",
    scope="group",
    icon="trophy",
    stages=(
        ("level_5", "Бронзовий старт", "Досягнуто 5 рівня у групі", 5),
        ("level_10", "Срібний ритм", "Досягнуто 10 рівня у групі", 10),
        ("level_20", "Золота хвиля", "Досягнуто 20 рівня у групі", 20),
        ("level_35", "Діамантовий пульс", "Досягнуто 35 рівня у групі", 35),
        ("level_50", "Майстер ChatPulse", "Досягнуто 50 рівня у групі", 50),
    ),
)

MEDIA_CHAIN = _chain(
    key="media_total",
    category="media",
    trigger="media_created",
    metric="media_count",
    scope="group",
    icon="gallery-horizontal",
    stages=(
        ("media_10", "Медіастарт", "Надіслано 10 медіаповідомлень", 10),
        ("media_50", "Стрічка оживає", "Надіслано 50 медіаповідомлень", 50),
        ("media_100", "Медіамейкер", "Надіслано 100 медіаповідомлень", 100),
        ("media_500", "Контент-машина", "Надіслано 500 медіаповідомлень", 500),
        ("media_1000", "Медіаархів", "Надіслано 1 000 медіаповідомлень", 1_000),
    ),
)

GLOBAL_XP_CHAIN = _chain(
    key="global_xp",
    category="global",
    trigger="level_changed",
    metric="global_xp_total",
    scope="global",
    icon="globe-2",
    stages=(
        ("global_xp_1000", "Глобальний старт", "Набрано 1 000 XP у ChatPulse", 1_000),
        ("global_xp_5000", "Помітний у мережі", "Набрано 5 000 XP у ChatPulse", 5_000),
        ("global_xp_10000", "Глобальний пульс", "Набрано 10 000 XP у ChatPulse", 10_000),
        ("global_xp_25000", "Міжгрупова легенда", "Набрано 25 000 XP у ChatPulse", 25_000),
        ("global_xp_100000", "Серце ChatPulse", "Набрано 100 000 XP у ChatPulse", 100_000),
    ),
)

GROUPS_CHAIN = _chain(
    key="groups",
    category="global",
    trigger="weekly_report_created",
    metric="groups_count",
    scope="global",
    icon="users-round",
    stages=(
        ("groups_2", "Між двома світами", "Активність у 2 групах", 2),
        ("groups_3", "Соціальний трикутник", "Активність у 3 групах", 3),
        ("groups_5", "Мережевий учасник", "Активність у 5 групах", 5),
        ("groups_10", "Всюди свій", "Активність у 10 групах", 10),
    ),
)

ACTIVE_DAYS_CHAIN = _chain(
    key="active_days",
    category="streak",
    trigger="weekly_report_created",
    metric="active_days_total",
    scope="global",
    icon="calendar-check-2",
    stages=(
        ("active_days_3", "Три активні дні", "Активність у 3 різні дні", 3),
        ("active_days_7", "Повний тиждень", "Активність у 7 різних днів", 7),
        ("active_days_30", "Місяць присутності", "Активність у 30 різних днів", 30),
        ("active_days_90", "Сезон разом", "Активність у 90 різних днів", 90),
        ("active_days_180", "Пів року присутності", "Активність у 180 різних днів", 180),
    ),
)

WEEKLY_XP_CHAIN = _chain(
    key="weekly_xp",
    category="activity",
    trigger="weekly_report_created",
    metric="xp_7d",
    scope="group",
    icon="calendar-days",
    stages=(
        ("weekly_xp_100", "Активний тиждень", "Набрано 100 XP за 7 днів", 100),
        ("weekly_xp_500", "Гаряча сімка", "Набрано 500 XP за 7 днів", 500),
        ("weekly_xp_1000", "Тижневий рекорд", "Набрано 1 000 XP за 7 днів", 1_000),
    ),
)

RANKING_ACHIEVEMENTS = (
    AchievementDefinition(
        code="rank_top_10",
        title="У десятці",
        description="Увійти до топ-10 групового рейтингу",
        category="ranking",
        rarity=AchievementRarity.RARE,
        scope="group",
        icon="list-ordered",
        visual_theme=RARITY_THEME[AchievementRarity.RARE],
        hidden=False,
        chain_key="ranking",
        chain_stage=1,
        chain_total=3,
        trigger="ranking_calculated",
        metric="rank",
        threshold=10,
        comparator="lte",
        reward_xp=20,
    ),
    AchievementDefinition(
        code="rank_top_3",
        title="На п’єдесталі",
        description="Увійти до топ-3 групового рейтингу",
        category="ranking",
        rarity=AchievementRarity.EPIC,
        scope="group",
        icon="medal",
        visual_theme=RARITY_THEME[AchievementRarity.EPIC],
        hidden=False,
        chain_key="ranking",
        chain_stage=2,
        chain_total=3,
        trigger="ranking_calculated",
        metric="rank",
        threshold=3,
        comparator="lte",
        important=True,
        reward_xp=40,
    ),
    AchievementDefinition(
        code="rank_1",
        title="Номер один",
        description="Посісти перше місце у груповому рейтингу",
        category="ranking",
        rarity=AchievementRarity.LEGENDARY,
        scope="group",
        icon="crown",
        visual_theme=RARITY_THEME[AchievementRarity.LEGENDARY],
        hidden=False,
        chain_key="ranking",
        chain_stage=3,
        chain_total=3,
        trigger="ranking_calculated",
        metric="rank",
        threshold=1,
        comparator="lte",
        important=True,
        reward_xp=75,
    ),
)

SECRET_ACHIEVEMENTS = (
    AchievementDefinition(
        code="secret_night_owl",
        title="Нічна сова",
        description="Надіслати 100 повідомлень у нічний час",
        category="secret",
        rarity=AchievementRarity.SECRET,
        scope="group",
        icon="moon-star",
        visual_theme=RARITY_THEME[AchievementRarity.SECRET],
        hidden=True,
        chain_key=None,
        chain_stage=0,
        chain_total=0,
        trigger="message_created",
        metric="night_messages_count",
        threshold=100,
        important=True,
        reward_xp=35,
    ),
    AchievementDefinition(
        code="secret_early_bird",
        title="Перший промінь",
        description="Надіслати 100 ранкових повідомлень",
        category="secret",
        rarity=AchievementRarity.SECRET,
        scope="group",
        icon="sunrise",
        visual_theme=RARITY_THEME[AchievementRarity.SECRET],
        hidden=True,
        chain_key=None,
        chain_stage=0,
        chain_total=0,
        trigger="message_created",
        metric="morning_messages_count",
        threshold=100,
        important=True,
        reward_xp=35,
    ),
    AchievementDefinition(
        code="secret_voice_marathon",
        title="Голосовий марафон",
        description="Надіслати 333 голосових повідомлення",
        category="secret",
        rarity=AchievementRarity.SECRET,
        scope="group",
        icon="audio-lines",
        visual_theme=RARITY_THEME[AchievementRarity.SECRET],
        hidden=True,
        chain_key=None,
        chain_stage=0,
        chain_total=0,
        trigger="media_created",
        metric="voice_count",
        threshold=333,
        important=True,
        reward_xp=50,
    ),
    AchievementDefinition(
        code="secret_photo_signal",
        title="Сигнал із 404 кадрів",
        description="Надіслати 404 фото",
        category="secret",
        rarity=AchievementRarity.SECRET,
        scope="group",
        icon="scan-search",
        visual_theme=RARITY_THEME[AchievementRarity.SECRET],
        hidden=True,
        chain_key=None,
        chain_stage=0,
        chain_total=0,
        trigger="media_created",
        metric="photo_count",
        threshold=404,
        important=True,
        reward_xp=50,
    ),
    AchievementDefinition(
        code="secret_reaction_storm",
        title="Емоційний шторм",
        description="Отримати 777 реакцій",
        category="secret",
        rarity=AchievementRarity.SECRET,
        scope="group",
        icon="cloud-lightning",
        visual_theme=RARITY_THEME[AchievementRarity.SECRET],
        hidden=True,
        chain_key=None,
        chain_stage=0,
        chain_total=0,
        trigger="reaction_received",
        metric="reactions_received",
        threshold=777,
        important=True,
        reward_xp=60,
    ),
    AchievementDefinition(
        code="secret_perfect_rhythm",
        title="Ідеальний ритм",
        description="Підтримувати серію активності 111 днів",
        category="secret",
        rarity=AchievementRarity.SECRET,
        scope="group",
        icon="orbit",
        visual_theme=RARITY_THEME[AchievementRarity.SECRET],
        hidden=True,
        chain_key=None,
        chain_stage=0,
        chain_total=0,
        trigger="streak_updated",
        metric="current_streak",
        threshold=111,
        important=True,
        reward_xp=70,
    ),
)

ACHIEVEMENTS: tuple[AchievementDefinition, ...] = (
    *MESSAGE_CHAIN,
    *REPLY_CHAIN,
    *REACTION_CHAIN,
    *PHOTO_CHAIN,
    *VOICE_CHAIN,
    *GROUP_XP_CHAIN,
    *STREAK_CHAIN,
    *LEVEL_CHAIN,
    *MEDIA_CHAIN,
    *GLOBAL_XP_CHAIN,
    *GROUPS_CHAIN,
    *ACTIVE_DAYS_CHAIN,
    *WEEKLY_XP_CHAIN,
    *RANKING_ACHIEVEMENTS,
    *SECRET_ACHIEVEMENTS,
)

ACHIEVEMENT_BY_CODE = {item.code: item for item in ACHIEVEMENTS}

_BY_TRIGGER: dict[AchievementTrigger, tuple[AchievementDefinition, ...]] = {}
_grouped: defaultdict[AchievementTrigger, list[AchievementDefinition]] = defaultdict(list)
for _definition in ACHIEVEMENTS:
    _grouped[_definition.trigger].append(_definition)
for _trigger, _definitions in _grouped.items():
    _BY_TRIGGER[_trigger] = tuple(_definitions)


def definitions_for_trigger(trigger: AchievementTrigger) -> tuple[AchievementDefinition, ...]:
    return _BY_TRIGGER.get(trigger, ())
