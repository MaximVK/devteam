import React, { useState } from 'react'
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material'
import { Add as AddIcon, Sync as SyncIcon } from '@mui/icons-material'
import { useQuery, useMutation } from 'react-query'
import { agentService, taskService } from '../services/api'

export default function Tasks() {
  const [open, setOpen] = useState(false)
  const [formData, setFormData] = useState({
    agent_role: '',
    task_title: '',
    task_description: '',
    github_issue_number: '',
  })

  const { data: agents } = useQuery('agents', () =>
    agentService.getAll().then((res) => res.data)
  )

  const assignMutation = useMutation(
    (data: any) => taskService.assign(data),
    {
      onSuccess: () => {
        setOpen(false)
        setFormData({
          agent_role: '',
          task_title: '',
          task_description: '',
          github_issue_number: '',
        })
      },
    }
  )

  const syncMutation = useMutation(() => taskService.syncGithub())

  const handleAssign = () => {
    const data = {
      ...formData,
      github_issue_number: formData.github_issue_number
        ? parseInt(formData.github_issue_number)
        : undefined,
    }
    assignMutation.mutate(data)
  }

  // Collect all tasks from agents
  const allTasks = agents?.flatMap((agent) => {
    const tasks = []
    if (agent.current_task) {
      tasks.push({
        ...agent.current_task,
        agent: agent.role,
        status: 'in_progress',
      })
    }
    return tasks
  }) || []

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Tasks</Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<SyncIcon />}
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isLoading}
            sx={{ mr: 2 }}
          >
            Sync GitHub
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpen(true)}
          >
            Assign Task
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Title</TableCell>
              <TableCell>Agent</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>GitHub Issue</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {allTasks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  No active tasks
                </TableCell>
              </TableRow>
            ) : (
              allTasks.map((task, index) => (
                <TableRow key={index}>
                  <TableCell>{task.title}</TableCell>
                  <TableCell>{task.agent.toUpperCase()}</TableCell>
                  <TableCell>{task.status}</TableCell>
                  <TableCell>
                    {task.github_issue_number ? `#${task.github_issue_number}` : '-'}
                  </TableCell>
                  <TableCell>
                    {new Date(task.created_at).toLocaleString()}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Assign New Task</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Agent</InputLabel>
            <Select
              value={formData.agent_role}
              label="Agent"
              onChange={(e) => setFormData({ ...formData, agent_role: e.target.value })}
            >
              {agents?.map((agent) => (
                <MenuItem key={agent.role} value={agent.role}>
                  {agent.role.toUpperCase()} ({agent.health})
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            fullWidth
            label="Task Title"
            value={formData.task_title}
            onChange={(e) => setFormData({ ...formData, task_title: e.target.value })}
            sx={{ mt: 2 }}
          />

          <TextField
            fullWidth
            label="Task Description"
            value={formData.task_description}
            onChange={(e) =>
              setFormData({ ...formData, task_description: e.target.value })
            }
            multiline
            rows={4}
            sx={{ mt: 2 }}
          />

          <TextField
            fullWidth
            label="GitHub Issue Number (optional)"
            value={formData.github_issue_number}
            onChange={(e) =>
              setFormData({ ...formData, github_issue_number: e.target.value })
            }
            type="number"
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            onClick={handleAssign}
            variant="contained"
            disabled={
              !formData.agent_role ||
              !formData.task_title ||
              assignMutation.isLoading
            }
          >
            Assign
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}