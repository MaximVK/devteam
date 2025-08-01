import React, { useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
  IconButton,
  Chip,
} from '@mui/material'
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Stop as StopIcon,
  Code as CodeIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useNavigate } from 'react-router-dom'
import { agentService, CreateAgentRequest } from '../services/api'

const ROLES = ['frontend', 'backend', 'database', 'qa', 'ba', 'teamlead']
const MODELS = [
  { value: 'claude-3-sonnet-20240229', label: 'Claude 3 Sonnet' },
  { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
]

export default function Agents() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [formData, setFormData] = useState<CreateAgentRequest>({
    role: '',
    model: 'claude-3-sonnet-20240229',
  })

  const { data: agents } = useQuery(
    'agents',
    () => agentService.getAll().then((res) => res.data),
    { refetchInterval: 5000 }
  )

  const createMutation = useMutation(
    (data: CreateAgentRequest) => agentService.create(data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('agents')
        setOpen(false)
        setFormData({ role: '', model: 'claude-3-sonnet-20240229' })
      },
    }
  )

  const restartMutation = useMutation(
    (role: string) => agentService.restart(role),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('agents')
      },
    }
  )

  const stopMutation = useMutation(
    (role: string) => agentService.stop(role),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('agents')
      },
    }
  )

  const handleCreate = () => {
    createMutation.mutate(formData)
  }

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'active':
        return 'success'
      case 'idle':
        return 'warning'
      default:
        return 'error'
    }
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Agents</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setOpen(true)}
        >
          Create Agent
        </Button>
      </Box>

      <Grid container spacing={3}>
        {agents?.map((agent) => (
          <Grid item xs={12} md={6} lg={4} key={agent.role}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="h5" component="div">
                    {agent.role.toUpperCase()}
                  </Typography>
                  <Chip
                    label={agent.health}
                    color={getHealthColor(agent.health)}
                    size="small"
                  />
                </Box>

                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Model: {agent.model}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Port: {agent.port}
                  </Typography>
                  {agent.process && (
                    <Typography variant="body2" color="text.secondary">
                      PID: {agent.process.pid || 'N/A'}
                    </Typography>
                  )}
                  <Typography variant="body2" color="text.secondary">
                    Tokens: {agent.total_tokens_used.toLocaleString()}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Tasks: {agent.task_history_count}
                  </Typography>
                </Box>

                {agent.current_task && (
                  <Box sx={{ mt: 2, p: 1, bgcolor: 'action.selected', borderRadius: 1 }}>
                    <Typography variant="body2" fontWeight="bold">
                      Current Task:
                    </Typography>
                    <Typography variant="body2">{agent.current_task.title}</Typography>
                  </Box>
                )}
              </CardContent>

              <CardActions>
                <IconButton
                  size="small"
                  onClick={() => navigate(`/claude/${agent.role}`)}
                  title="Edit CLAUDE.md"
                >
                  <CodeIcon />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={() => restartMutation.mutate(agent.role)}
                  disabled={restartMutation.isLoading}
                  title="Restart Agent"
                >
                  <RefreshIcon />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={() => stopMutation.mutate(agent.role)}
                  disabled={stopMutation.isLoading}
                  color="error"
                  title="Stop Agent"
                >
                  <StopIcon />
                </IconButton>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Agent</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Role</InputLabel>
            <Select
              value={formData.role}
              label="Role"
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
            >
              {ROLES.map((role) => (
                <MenuItem key={role} value={role}>
                  {role.toUpperCase()}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Model</InputLabel>
            <Select
              value={formData.model}
              label="Model"
              onChange={(e) => setFormData({ ...formData, model: e.target.value })}
            >
              {MODELS.map((model) => (
                <MenuItem key={model.value} value={model.value}>
                  {model.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            fullWidth
            label="GitHub Repository (optional)"
            value={formData.github_repo || ''}
            onChange={(e) => setFormData({ ...formData, github_repo: e.target.value })}
            sx={{ mt: 2 }}
          />

          <TextField
            fullWidth
            label="Telegram Channel ID (optional)"
            value={formData.telegram_channel_id || ''}
            onChange={(e) =>
              setFormData({ ...formData, telegram_channel_id: e.target.value })
            }
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreate}
            variant="contained"
            disabled={!formData.role || createMutation.isLoading}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}