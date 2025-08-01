import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface Agent {
  role: string
  port: number
  model: string
  current_task: any
  task_history_count: number
  last_activity: string
  total_tokens_used: number
  health: string
  process?: {
    pid: number | null
    status: string
    uptime?: number
  }
}

export interface CreateAgentRequest {
  role: string
  model?: string
  github_repo?: string
  telegram_channel_id?: string
}

export interface SystemConfig {
  telegram_bot_token?: string
  telegram_channel_id?: string
  github_token?: string
  github_repo?: string
  anthropic_api_key: string
}

export const agentService = {
  getAll: () => api.get<Agent[]>('/agents'),
  getOne: (role: string) => api.get<Agent>(`/agents/${role}`),
  create: (data: CreateAgentRequest) => api.post('/agents', data),
  restart: (role: string) => api.post(`/agents/${role}/restart`),
  stop: (role: string) => api.delete(`/agents/${role}`),
  getLogs: (role: string, limit = 50) =>
    api.get(`/agents/${role}/logs?limit=${limit}`),
}

export const taskService = {
  assign: (data: {
    agent_role: string
    task_title: string
    task_description: string
    github_issue_number?: number
  }) => api.post('/tasks/assign', data),
  syncGithub: () => api.post('/tasks/sync-github'),
}

export const claudeService = {
  getPrompt: (role: string) => api.get(`/claude/${role}`),
  updatePrompt: (role: string, content: string) =>
    api.put(`/claude/${role}`, { content }),
}

export const systemService = {
  initialize: (config: SystemConfig) => api.post('/system/initialize', config),
}

export default api