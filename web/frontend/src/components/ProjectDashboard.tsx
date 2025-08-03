import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Button,
  Chip,
  Menu,
  MenuItem,
  Grid,
  Card,
  CardContent,
  CardActions,
  Avatar,
  AvatarGroup,
  Tooltip,
  CircularProgress,
  Divider
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import FolderIcon from '@mui/icons-material/Folder';
import PersonIcon from '@mui/icons-material/Person';
import GitHubIcon from '@mui/icons-material/GitHub';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import PauseCircleIcon from '@mui/icons-material/PauseCircle';
import api from '../services/api';
import { CreateProjectDialog } from './CreateProjectDialog';
import { CreateAgentDialog } from './CreateAgentDialog';

interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
  last_accessed: string;
  agent_count: number;
  status: string;
  is_current: boolean;
}

interface ProjectDetails {
  id: string;
  name: string;
  description: string;
  repository: {
    url: string;
    base_branch: string;
  };
  agents: Record<string, {
    role: string;
    name: string;
    status: string;
    last_active: string;
  }>;
}

export const ProjectDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<ProjectDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const [createAgentOpen, setCreateAgentOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const response = await api.get('/app/projects');
      setProjects(response.data);
      
      // Load current project details
      const currentProj = response.data.find((p: Project) => p.is_current);
      if (currentProj) {
        await loadProjectDetails(currentProj.id);
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadProjectDetails = async (projectId: string) => {
    try {
      const response = await api.get(`/app/projects/${projectId}`);
      setCurrentProject(response.data);
    } catch (error) {
      console.error('Failed to load project details:', error);
    }
  };

  const handleSwitchProject = async (projectId: string) => {
    try {
      await api.post(`/app/projects/${projectId}/switch`);
      await loadProjects();
    } catch (error) {
      console.error('Failed to switch project:', error);
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

  const handleCreateAgent = async (agentData: any) => {
    if (!currentProject) return;
    
    try {
      await api.post(`/app/projects/${currentProject.id}/agents`, agentData);
      setCreateAgentOpen(false);
      await loadProjectDetails(currentProject.id);
    } catch (error) {
      console.error('Failed to create agent:', error);
      throw error;
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

  const getAgentAvatar = (agent: any) => {
    const colors: Record<string, string> = {
      backend: '#2196f3',
      frontend: '#4caf50',
      database: '#ff9800',
      qa: '#9c27b0',
      ba: '#00bcd4',
      teamlead: '#f44336',
      devops: '#795548',
      security: '#607d8b'
    };
    
    return (
      <Tooltip title={`${agent.name} (${agent.role})`}>
        <Avatar sx={{ bgcolor: colors[agent.role] || '#9e9e9e', width: 32, height: 32 }}>
          {agent.name[0].toUpperCase()}
        </Avatar>
      </Tooltip>
    );
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
      <Grid container spacing={3}>
        {/* Projects List */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">Projects</Typography>
              <Button
                startIcon={<AddIcon />}
                variant="contained"
                size="small"
                onClick={() => setCreateProjectOpen(true)}
              >
                New Project
              </Button>
            </Box>
            
            <List>
              {projects.map((project) => (
                <ListItem
                  key={project.id}
                  button
                  selected={project.is_current}
                  onClick={() => handleSwitchProject(project.id)}
                >
                  <ListItemText
                    primary={project.name}
                    secondary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="caption">
                          {project.agent_count} agents
                        </Typography>
                        {project.is_current && (
                          <Chip label="Active" size="small" color="primary" />
                        )}
                      </Box>
                    }
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      onClick={(e) => handleProjectMenu(e, project.id)}
                    >
                      <MoreVertIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>

        {/* Current Project Details */}
        <Grid item xs={12} md={8}>
          {currentProject ? (
            <Paper sx={{ p: 3 }}>
              <Box display="flex" alignItems="center" gap={2} mb={3}>
                <FolderIcon sx={{ fontSize: 40, color: 'primary.main' }} />
                <Box flex={1}>
                  <Typography variant="h5">{currentProject.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {currentProject.description}
                  </Typography>
                </Box>
              </Box>

              <Box display="flex" alignItems="center" gap={2} mb={3}>
                <GitHubIcon />
                <Typography variant="body2" color="text.secondary">
                  {currentProject.repository.url}
                </Typography>
                <Chip 
                  label={currentProject.repository.base_branch} 
                  size="small" 
                  variant="outlined" 
                />
              </Box>

              <Divider sx={{ my: 3 }} />

              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">Project Agents</Typography>
                <Button
                  startIcon={<AddIcon />}
                  variant="outlined"
                  size="small"
                  onClick={() => setCreateAgentOpen(true)}
                >
                  Add Agent
                </Button>
              </Box>

              <Grid container spacing={2}>
                {Object.entries(currentProject.agents).map(([agentId, agent]) => (
                  <Grid item xs={12} sm={6} md={4} key={agentId}>
                    <Card>
                      <CardContent>
                        <Box display="flex" alignItems="center" gap={2} mb={2}>
                          {getAgentAvatar(agent)}
                          <Box>
                            <Typography 
                              variant="h6" 
                              sx={{ 
                                cursor: 'pointer', 
                                '&:hover': { color: 'primary.main', textDecoration: 'underline' } 
                              }}
                              onClick={() => navigate(`/projects/${currentProject.id}/agents/${agentId}`)}
                            >
                              {agent.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {agent.role}
                            </Typography>
                          </Box>
                        </Box>
                        
                        <Box display="flex" alignItems="center" gap={1}>
                          {agent.status === 'active' ? (
                            <CheckCircleIcon color="success" fontSize="small" />
                          ) : (
                            <PauseCircleIcon color="disabled" fontSize="small" />
                          )}
                          <Typography variant="body2">
                            {agent.status}
                          </Typography>
                        </Box>
                        
                        <Typography variant="caption" color="text.secondary" display="block" mt={1}>
                          Last active: {new Date(agent.last_active).toLocaleDateString()}
                        </Typography>
                      </CardContent>
                      <CardActions>
                        <Button 
                          size="small" 
                          onClick={() => navigate(`/projects/${currentProject.id}/agents/${agentId}`)}
                        >
                          View Details
                        </Button>
                        <Button size="small" color="error">Remove</Button>
                      </CardActions>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Paper>
          ) : (
            <Paper sx={{ p: 3 }}>
              <Box textAlign="center" py={5}>
                <FolderIcon sx={{ fontSize: 60, color: 'text.disabled', mb: 2 }} />
                <Typography variant="h6" color="text.secondary">
                  No project selected
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={3}>
                  Create a new project or select an existing one to get started
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
        </Grid>
      </Grid>

      {/* Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={() => setMenuAnchor(null)}
      >
        <MenuItem onClick={handleArchiveProject}>Archive Project</MenuItem>
      </Menu>

      {/* Dialogs */}
      <CreateProjectDialog
        open={createProjectOpen}
        onClose={() => setCreateProjectOpen(false)}
        onCreate={handleCreateProject}
      />
      
      <CreateAgentDialog
        open={createAgentOpen}
        onClose={() => setCreateAgentOpen(false)}
        onCreate={handleCreateAgent}
      />
    </Box>
  );
};