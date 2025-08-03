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

// App/Project-based API services
export interface Project {
  id: string
  name: string
  description: string
  created_at: string
  last_accessed: string
  agent_count: number
  status: string
  is_current: boolean
}

export interface ProjectAgent {
  role: string
  name: string
  status: string
  last_active: string
}

export interface AgentConfig {
  agent_id: string
  permissions: {
    allowed_paths: string[]
    allowed_commands: string[]
    can_access_internet: boolean
    can_install_packages: boolean
    can_modify_git_config: boolean
    max_file_size_mb: number
    max_command_output_lines: number
  }
  settings: {
    enabled: boolean
    auto_start: boolean
    model: string
    max_tokens: number
    temperature: number
    system_prompt_additions: string
    memory_limit_mb: number
    cpu_limit_percent: number
  }
  custom_tools: Record<string, any>
  environment: Record<string, string>
}

export const appService = {
  // Projects
  getProjects: () => api.get<Project[]>('/app/projects'),
  getProject: (projectId: string) => api.get(`/app/projects/${projectId}`),
  createProject: (data: any) => api.post('/app/projects', data),
  switchProject: (projectId: string) => api.post(`/app/projects/${projectId}/switch`),
  deleteProject: (projectId: string) => api.delete(`/app/projects/${projectId}`),
  
  // Agents
  createAgent: (projectId: string, data: any) => api.post(`/app/projects/${projectId}/agents`, data),
  getAgentConfig: (projectId: string, agentId: string) => 
    api.get<AgentConfig>(`/app/projects/${projectId}/agents/${agentId}/config`),
  updateAgentConfig: (projectId: string, agentId: string, config: AgentConfig) => 
    api.put(`/app/projects/${projectId}/agents/${agentId}/config`, config),
  getAgentLogs: (projectId: string, agentId: string, lines = 100) => 
    api.get(`/app/projects/${projectId}/agents/${agentId}/logs?lines=${lines}`),
  getAgentCommands: (projectId: string, agentId: string, limit = 50) => 
    api.get(`/app/projects/${projectId}/agents/${agentId}/commands?limit=${limit}`),
  
  // App status
  getStatus: () => api.get('/app/status'),
}

export default api