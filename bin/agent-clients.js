import { homedir } from "node:os";
import { join, resolve } from "node:path";

export const DEFAULT_AGENT_CLIENT = "codex";

const CLIENTS = [
  {
    id: "codex",
    displayName: "Codex",
    aliases: ["codex"],
    skillsDir(environment, home) {
      const codexHome = environment.CODEX_HOME
        ? resolve(environment.CODEX_HOME)
        : join(home, ".codex");
      return join(codexHome, "skills");
    },
  },
  {
    id: "claude-code",
    displayName: "Claude Code",
    aliases: ["claude-code", "claude"],
    skillsDir(_environment, home) {
      return join(home, ".claude", "skills");
    },
  },
  {
    id: "opencode",
    displayName: "OpenCode",
    aliases: ["opencode", "open-code"],
    skillsDir(environment, home) {
      const configHome = environment.XDG_CONFIG_HOME
        ? resolve(environment.XDG_CONFIG_HOME)
        : join(home, ".config");
      return join(configHome, "opencode", "skills");
    },
  },
  {
    id: "gemini",
    displayName: "Gemini CLI",
    aliases: ["gemini", "gemini-cli"],
    skillsDir(_environment, home) {
      return join(home, ".gemini", "skills");
    },
  },
  {
    id: "copilot",
    displayName: "GitHub Copilot",
    aliases: ["copilot", "github-copilot"],
    skillsDir(_environment, home) {
      return join(home, ".copilot", "skills");
    },
  },
  {
    id: "qwen-code",
    displayName: "Qwen Code",
    aliases: ["qwen-code", "qwen"],
    skillsDir(_environment, home) {
      return join(home, ".qwen", "skills");
    },
  },
  {
    id: "windsurf",
    displayName: "Windsurf Cascade",
    aliases: ["windsurf", "cascade"],
    skillsDir(_environment, home) {
      return join(home, ".codeium", "windsurf", "skills");
    },
  },
  {
    id: "cline",
    displayName: "Cline",
    aliases: ["cline"],
    activationNote:
      "Cline may require Settings > Features > Enable Skills before discovery.",
    skillsDir(_environment, home) {
      return join(home, ".cline", "skills");
    },
  },
  {
    id: "kiro",
    displayName: "Kiro",
    aliases: ["kiro", "kiro-cli"],
    skillsDir(_environment, home) {
      return join(home, ".kiro", "skills");
    },
  },
];

const CLIENT_BY_ALIAS = new Map(
  CLIENTS.flatMap((client) =>
    client.aliases.map((alias) => [alias, client]),
  ),
);

function userHome(environment) {
  if (process.platform === "win32") {
    if (environment.USERPROFILE) {
      return resolve(environment.USERPROFILE);
    }
    if (environment.HOMEDRIVE && environment.HOMEPATH) {
      return resolve(`${environment.HOMEDRIVE}${environment.HOMEPATH}`);
    }
  } else if (environment.HOME) {
    return resolve(environment.HOME);
  }
  return homedir();
}

export function listAgentClients() {
  return CLIENTS;
}

export function resolveAgentClient(identifier) {
  return CLIENT_BY_ALIAS.get(String(identifier).trim().toLowerCase()) ?? null;
}

export function requireAgentClient(identifier) {
  const client = resolveAgentClient(identifier);
  if (!client) {
    throw new Error(
      `unsupported client: ${identifier}; supported clients: ${CLIENTS.map((item) => item.id).join(", ")}`,
    );
  }
  return client;
}

export function defaultSkillsDir(client, environment = process.env) {
  const resolvedClient =
    typeof client === "string" ? requireAgentClient(client) : client;
  return resolvedClient.skillsDir(environment, userHome(environment));
}

export function clientSessionHint(client, skillName) {
  const lines = [
    `Start a new ${client.displayName} session, then ask it to use ${skillName}.`,
  ];
  if (client.activationNote) {
    lines.push(client.activationNote);
  }
  return lines.join("\n");
}
