export const appPaths = {
  root: "/miniapp",
  home: "/miniapp",
  groups: "/miniapp/groups",
  group: (telegramChatId: number | string) => `/miniapp/groups/${telegramChatId}`,
  achievements: "/miniapp/achievements",
  profile: "/miniapp/profile",
  vip: "/miniapp/vip",
  owner: {
    root: "/miniapp/owner",
    users: "/miniapp/owner/users",
    user: (telegramId: number | string) => `/miniapp/owner/users/${telegramId}`,
    groups: "/miniapp/owner/groups",
    payments: "/miniapp/owner/payments",
    audit: "/miniapp/owner/audit",
  },
} as const;
