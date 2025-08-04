import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Button,
  IconButton,
  Chip,
  Tooltip,
  CircularProgress,
  Menu,
  MenuItem,
  Avatar,
  AvatarGroup
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import GitHubIcon from '@mui/icons-material/GitHub';
import GroupIcon from '@mui/icons-material/Group';
import RefreshIcon from '@mui/icons-material/Refresh';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { CreateProjectDialog } from './CreateProjectDialog';

interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
  last_accessed: string;
  agent_count: number;
  status: string;
  is_current: boolean;
  repository_url?: string;
}

interface AgentStatus {
  [agentId: string]: {
    running: boolean;
    pid?: number;
  };
}

interface ProjectStatus {
  agents: AgentStatus;
  total_agents: number;
  running_agents: number;
}

export const ProjectList: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectStatus, setProjectStatus] = useState<Record<string, ProjectStatus>>({});
  const [loading, setLoading] = useState(true);
  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [startingProjects, setStartingProjects] = useState<Set<string>>(new Set());
  const [stoppingProjects, setStoppingProjects] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadProjects();
    loadAgentStatus();
    // Refresh status every 5 seconds
    const interval = setInterval(loadAgentStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadProjects = async () => {
    try {
      const response = await api.get('/app/projects');
      setProjects(response.data);
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAgentStatus = async () => {
    try {
      const response = await api.get('/app/agents/status');
      setProjectStatus(response.data.projects || {});
    } catch (error) {
      console.error('Failed to load agent status:', error);
    }
  };

  const handleCreateProject = async (projectData: any) => {
    try {
      await api.post('/app/projects', projectData);
      setCreateProjectOpen(false);
      await loadProjects();
    } catch (error) {
      console.error('Failed to create project:', error);
      throw error;
    }
  };

  const handleStartAgents = async (projectId: string) => {
    setStartingProjects(prev => new Set(prev).add(projectId));
    try {
      await api.post(`/app/projects/${projectId}/agents/start`);
      // Wait a bit for agents to start
      setTimeout(() => {
        loadAgentStatus();
        setStartingProjects(prev => {
          const next = new Set(prev);
          next.delete(projectId);
          return next;
        });
      }, 2000);
    } catch (error) {
      console.error('Failed to start agents:', error);
      setStartingProjects(prev => {
        const next = new Set(prev);
        next.delete(projectId);
        return next;
      });
    }
  };

  const handleStopAgents = async (projectId: string) => {
    setStoppingProjects(prev => new Set(prev).add(projectId));
    try {
      await api.post(`/app/projects/${projectId}/agents/stop`);
      // Wait a bit for agents to stop
      setTimeout(() => {
        loadAgentStatus();
        setStoppingProjects(prev => {
          const next = new Set(prev);
          next.delete(projectId);
          return next;
        });
      }, 1000);
    } catch (error) {
      console.error('Failed to stop agents:', error);
      setStoppingProjects(prev => {
        const next = new Set(prev);
        next.delete(projectId);
        return next;
      });
    }
  };

  const handleProjectMenu = (event: React.MouseEvent<HTMLElement>, projectId: string) => {
    setMenuAnchor(event.currentTarget);
    setSelectedProjectId(projectId);
  };

  const handleArchiveProject = async () => {
    if (!selectedProjectId) return;
    
    try {
      await api.delete(`/app/projects/${selectedProjectId}`);
      setMenuAnchor(null);
      await loadProjects();
    } catch (error) {
      console.error('Failed to archive project:', error);
    }
  };

  const handleManageProject = (projectId: string) => {
    navigate(`/projects/${projectId}`);
  };

  const getProjectStatus = (projectId: string) => {
    const project = projects.find(p => p.id === projectId);
    const status = projectStatus[projectId];
    
    // Use agent_count from project data as the total
    const total = project?.agent_count || 0;
    const runningCount = status?.running_agents || 0;
    
    return {
      running: runningCount > 0,
      total: total,
      runningCount: runningCount
    };
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Projects</Typography>
        <Box display="flex" gap={2}>
          <Button
            startIcon={<RefreshIcon />}
            onClick={() => {
              loadProjects();
              loadAgentStatus();
            }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateProjectOpen(true)}
          >
            Create Project
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Project Name</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Repository</TableCell>
              <TableCell align="center">Agents</TableCell>
              <TableCell align="center">Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {projects.map((project) => {
              const status = getProjectStatus(project.id);
              const isStarting = startingProjects.has(project.id);
              const isStopping = stoppingProjects.has(project.id);
              const isProcessing = isStarting || isStopping;
              
              return (
                <TableRow key={project.id} hover>
                  <TableCell>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {project.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {project.description || 'No description'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={0.5}>
                      <GitHubIcon fontSize="small" color="action" />
                      <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                        {project.repository_url || 'N/A'}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <Box display="flex" alignItems="center" justifyContent="center" gap={1}>
                      <GroupIcon fontSize="small" color="action" />
                      <Typography variant="body2">
                        {status.runningCount}/{status.total}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    {isProcessing ? (
                      <CircularProgress size={20} />
                    ) : status.running ? (
                      <Chip 
                        icon={<CheckCircleIcon />} 
                        label="Running" 
                        size="small" 
                        color="success" 
                      />
                    ) : (
                      <Chip 
                        icon={<CancelIcon />} 
                        label="Stopped" 
                        size="small" 
                        color="default" 
                      />
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <Box display="flex" gap={1} justifyContent="flex-end">
                      {status.running ? (
                        <Tooltip title="Stop Agents">
                          <IconButton
                            color="error"
                            onClick={() => handleStopAgents(project.id)}
                            disabled={isProcessing}
                            size="small"
                          >
                            <StopIcon />
                          </IconButton>
                        </Tooltip>
                      ) : (
                        <Tooltip title="Start Agents">
                          <IconButton
                            color="primary"
                            onClick={() => handleStartAgents(project.id)}
                            disabled={isProcessing || status.total === 0}
                            size="small"
                          >
                            <PlayArrowIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Button
                        size="small"
                        onClick={() => handleManageProject(project.id)}
                      >
                        Manage
                      </Button>
                      <IconButton
                        size="small"
                        onClick={(e) => handleProjectMenu(e, project.id)}
                      >
                        <MoreVertIcon />
                      </IconButton>
                    </Box>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {projects.length === 0 && (
        <Paper sx={{ p: 4, mt: 2 }}>
          <Box textAlign="center">
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No projects yet
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={3}>
              Create your first project to get started
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setCreateProjectOpen(true)}
            >
              Create First Project
            </Button>
          </Box>
        </Paper>
      )}

      {/* Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={() => setMenuAnchor(null)}
      >
        <MenuItem onClick={handleArchiveProject}>Archive Project</MenuItem>
      </Menu>

      {/* Create Project Dialog */}
      <CreateProjectDialog
        open={createProjectOpen}
        onClose={() => setCreateProjectOpen(false)}
        onCreate={handleCreateProject}
      />
    </Box>
  );
};