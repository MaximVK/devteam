import React, { useEffect, useState } from 'react'
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Chip,
  LinearProgress,
} from '@mui/material'
import { useQuery } from 'react-query'
import { agentService, Agent } from '../services/api'

export default function Dashboard() {
  const { data: agents, isLoading } = useQuery(
    'agents',
    () => agentService.getAll().then((res) => res.data),
    { refetchInterval: 5000 }
  )

  const [ws, setWs] = useState<WebSocket | null>(null)

  useEffect(() => {
    const websocket = new WebSocket('ws://localhost:8000/ws')
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'agents_update') {
        // Handle real-time updates
      }
    }

    setWs(websocket)

    return () => {
      websocket.close()
    }
  }, [])

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

  if (isLoading) {
    return <LinearProgress />
  }

  const activeAgents = agents?.filter((a) => a.health === 'active') || []
  const totalTasks = agents?.reduce((sum, a) => sum + a.task_history_count, 0) || 0
  const totalTokens = agents?.reduce((sum, a) => sum + a.total_tokens_used, 0) || 0

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Agents
              </Typography>
              <Typography variant="h3">
                {activeAgents.length}/{agents?.length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Tasks
              </Typography>
              <Typography variant="h3">{totalTasks}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Tokens Used
              </Typography>
              <Typography variant="h3">
                {(totalTokens / 1000).toFixed(1)}k
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Est. Cost
              </Typography>
              <Typography variant="h3">
                ${((totalTokens / 1000000) * 3).toFixed(2)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Typography variant="h5" gutterBottom sx={{ mt: 3 }}>
        Agent Status
      </Typography>

      <Grid container spacing={2}>
        {agents?.map((agent) => (
          <Grid item xs={12} md={6} lg={4} key={agent.role}>
            <Paper sx={{ p: 2 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="h6">{agent.role.toUpperCase()}</Typography>
                <Chip
                  label={agent.health}
                  color={getHealthColor(agent.health)}
                  size="small"
                />
              </Box>

              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="textSecondary">
                  Model: {agent.model}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Port: {agent.port}
                </Typography>
                {agent.current_task && (
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Current: {agent.current_task.title}
                  </Typography>
                )}
                <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                  Tasks completed: {agent.task_history_count}
                </Typography>
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}