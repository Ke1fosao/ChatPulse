import type { AccountAccess, HomePayload } from "../../api/types";

export interface ProfileStatus {
  role: "CREATOR" | "VIP" | "MEMBER";
  plan: "OWNER ACCESS" | "PREMIUM" | "FREE";
  access: string;
  description: string;
  tone: "owner" | "vip" | "free";
}

export function getProfileStatus(account: AccountAccess): ProfileStatus {
  if (account.is_owner) {
    return {
      role: "CREATOR",
      plan: "OWNER ACCESS",
      access: "Назавжди",
      description: "Засновник і єдиний власник ChatPulse",
      tone: "owner",
    };
  }

  if (account.is_vip) {
    return {
      role: "VIP",
      plan: "PREMIUM",
      access: account.vip_expires_at
        ? `До ${new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium" }).format(
            new Date(account.vip_expires_at),
          )}`
        : "Безстроково",
      description: "Усі платні функції ChatPulse активні",
      tone: "vip",
    };
  }

  return {
    role: "MEMBER",
    plan: "FREE",
    access: "Стандартний доступ",
    description: "Основна аналітика, рівні та досягнення",
    tone: "free",
  };
}

const transliteration: Record<string, string> = {
  а: "a",
  б: "b",
  в: "v",
  г: "h",
  ґ: "g",
  д: "d",
  е: "e",
  є: "ie",
  ж: "zh",
  з: "z",
  и: "y",
  і: "i",
  ї: "i",
  й: "i",
  к: "k",
  л: "l",
  м: "m",
  н: "n",
  о: "o",
  п: "p",
  р: "r",
  с: "s",
  т: "t",
  у: "u",
  ф: "f",
  х: "kh",
  ц: "ts",
  ч: "ch",
  ш: "sh",
  щ: "shch",
  ь: "",
  ю: "iu",
  я: "ia",
};

export function profileCardFilename(data: HomePayload): string {
  const slug = data.user.display_name
    .trim()
    .toLocaleLowerCase("uk-UA")
    .split("")
    .map((character) => transliteration[character] ?? character)
    .join("")
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "profile";

  return `chatpulse-${slug}-level-${data.global_progress.level}.png`;
}

export function buildProfileShareText(data: HomePayload): string {
  const status = getProfileStatus(data.account);
  const progress = data.global_progress;
  const streak = data.quick_stats.current_streak;
  return [
    `Мій ChatPulse · ${status.role}`,
    `Рівень ${progress.level}/${data.level_catalog.max_level} · ${progress.tier}`,
    `${progress.xp_total.toLocaleString("uk-UA")} XP · місце #${progress.rank}`,
    `Серія: ${streak} дн.`,
  ].join("\n");
}
