import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardActions,
  Avatar,
  Chip,
  Divider,
  IconButton,
  TextField,
  Switch,
  FormControlLabel,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AddIcon from '@mui/icons-material/Add';
import GitHubIcon from '@mui/icons-material/GitHub';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import PauseCircleIcon from '@mui/icons-material/PauseCircle';
import DeleteIcon from '@mui/icons-material/Delete';
import TelegramIcon from '@mui/icons-material/Telegram';
import SaveIcon from '@mui/icons-material/Save';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import SettingsIcon from '@mui/icons-material/Settings';
import Snackbar from '@mui/material/Snackbar';
import api from '../services/api';
import { CreateAgentDialog } from './CreateAgentDialog';
import { AgentLogs } from './AgentLogs';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`project-tabpanel-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

interface ProjectDetails {
  id: string;
  name: string;
  folder_name?: string;
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
  telegram_config?: {
    bot_token: string;
    group_id: string;
    enabled: boolean;
  };
}

interface AgentStatus {
  [agentId: string]: {
    running: boolean;
    pid?: number;
    branch?: string;
    has_changes?: boolean;
  };
}

export const ProjectDetail: React.FC = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectDetails | null>(null);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>({});
  const [loading, setLoading] = useState(true);
  const [tabValue, setTabValue] = useState(0);
  const [createAgentOpen, setCreateAgentOpen] = useState(false);
  const [telegramConfig, setTelegramConfig] = useState({
    bot_token: '',
    group_id: '',
    enabled: false
  });
  const [savingTelegram, setSavingTelegram] = useState(false);
  const [agentsRunning, setAgentsRunning] = useState(false);
  const [processingAgents, setProcessingAgents] = useState(false);
  const [projectConfig, setProjectConfig] = useState({
    name: '',
    description: '',
    folder_name: ''
  });
  const [savingProject, setSavingProject] = useState(false);
  const [showSaveSuccess, setShowSaveSuccess] = useState(false);
  const [logsDialog, setLogsDialog] = useState<{
    open: boolean;
    agentId: string;
    agentName: string;
  }>({ open: false, agentId: '', agentName: '' });

  useEffect(() => {
    if (projectId) {
      loadProjectDetails();
      loadAgentStatus();
      // Refresh status every 3 seconds
      const interval = setInterval(loadAgentStatus, 3000);
      return () => clearInterval(interval);
    }
  }, [projectId]);

  const loadProjectDetails = async () => {
    if (!projectId) return;
    
    try {
      const response = await api.get(`/app/projects/${projectId}`);
      setProject(response.data);
      
      // Set telegram config
      if (response.data.telegram_config) {
        setTelegramConfig(response.data.telegram_config);
      }
      
      // Set project config
      setProjectConfig({
        name: response.data.name,
        description: response.data.description || '',
        folder_name: response.data.folder_name || ''
      });
    } catch (error) {
      console.error('Failed to load project details:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAgentStatus = async () => {
    if (!projectId) return;
    
    try {
      const response = await api.get(`/app/projects/${projectId}/agents/status`);
      setAgentStatus(response.data.agents || {});
      
      // Check if any agents are running
      const hasRunning = Object.values(response.data.agents || {}).some(
        (agent: any) => agent.running
      );
      setAgentsRunning(hasRunning);
    } catch (error) {
      console.error('Failed to load agent status:', error);
    }
  };

  const handleCreateAgent = async (agentData: any) => {
    if (!projectId) return;
    
    try {
      await api.post(`/app/projects/${projectId}/agents`, agentData);
      setCreateAgentOpen(false);
      await loadProjectDetails();
    } catch (error) {
      console.error('Failed to create agent:', error);
      throw error;
    }
  };

  const handleRemoveAgent = async (agentId: string) => {
    if (!projectId || !window.confirm('Are you sure you want to remove this agent?')) return;
    
    try {
      await api.delete(`/app/projects/${projectId}/agents/${agentId}`);
      await loadProjectDetails();
    } catch (error) {
      console.error('Failed to remove agent:', error);
    }
  };

  const handleSaveTelegramConfig = async () => {
    if (!projectId) return;
    
    setSavingTelegram(true);
    try {
      await api.put(`/app/projects/${projectId}/telegram`, telegramConfig);
      await loadProjectDetails();
      setShowSaveSuccess(true);
      setTimeout(() => setShowSaveSuccess(false), 3000);
    } catch (error) {
      console.error('Failed to save Telegram config:', error);
    } finally {
      setSavingTelegram(false);
    }
  };
  
  const handleSaveProjectConfig = async () => {
    if (!projectId) return;
    
    setSavingProject(true);
    try {
      await api.put(`/app/projects/${projectId}/config`, projectConfig);
      await loadProjectDetails();
      setShowSaveSuccess(true);
      setTimeout(() => setShowSaveSuccess(false), 3000);
    } catch (error) {
      console.error('Failed to save project config:', error);
    } finally {
      setSavingProject(false);
    }
  };

  const handleStartAgents = async () => {
    if (!projectId) return;
    
    setProcessingAgents(true);
    try {
      await api.post(`/app/projects/${projectId}/agents/start`);
      // Wait for agents to start
      setTimeout(() => {
        loadAgentStatus();
        setProcessingAgents(false);
      }, 2000);
    } catch (error) {
      console.error('Failed to start agents:', error);
      setProcessingAgents(false);
    }
  };

  const handleStopAgents = async () => {
    if (!projectId) return;
    
    setProcessingAgents(true);
    try {
      await api.post(`/app/projects/${projectId}/agents/stop`);
      // Wait for agents to stop
      setTimeout(() => {
        loadAgentStatus();
        setProcessingAgents(false);
      }, 1000);
    } catch (error) {
      console.error('Failed to stop agents:', error);
      setProcessingAgents(false);
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
      <Avatar sx={{ bgcolor: colors[agent.role] || '#9e9e9e', width: 40, height: 40 }}>
        {agent.name[0].toUpperCase()}
      </Avatar>
    );
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!project) {
    return (
      <Box>
        <Alert severity="error">Project not found</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/projects')}>
          Back to Projects
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <IconButton onClick={() => navigate('/projects')}>
          <ArrowBackIcon />
        </IconButton>
        <Box flex={1}>
          <Typography variant="h4">{project.name}</Typography>
          <Typography variant="body2" color="text.secondary">
            {project.description}
          </Typography>
        </Box>
        <Box>
          {processingAgents ? (
            <CircularProgress size={30} />
          ) : agentsRunning ? (
            <Button
              variant="outlined"
              color="error"
              startIcon={<StopIcon />}
              onClick={handleStopAgents}
            >
              Stop All Agents
            </Button>
          ) : (
            <Button
              variant="contained"
              startIcon={<PlayArrowIcon />}
              onClick={handleStartAgents}
              disabled={Object.keys(project.agents).length === 0}
            >
              Start All Agents
            </Button>
          )}
        </Box>
      </Box>

      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <GitHubIcon />
        <Typography variant="body2" color="text.secondary">
          {project.repository.url}
        </Typography>
        <Chip 
          label={project.repository.base_branch} 
          size="small" 
          variant="outlined" 
        />
      </Box>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="Agents" />
          <Tab label="Configuration" />
          <Tab label="Logs" />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h6">Project Agents</Typography>
          <Button
            startIcon={<AddIcon />}
            variant="outlined"
            onClick={() => setCreateAgentOpen(true)}
          >
            Add Agent
          </Button>
        </Box>

        <Grid container spacing={2}>
          {Object.entries(project.agents).map(([agentId, agent]) => {
            const status = agentStatus[agentId];
            const isRunning = status?.running || false;
            
            return (
              <Grid item xs={12} sm={6} md={4} key={agentId}>
                <Card>
                  <CardContent>
                    <Box display="flex" alignItems="center" gap={2} mb={2}>
                      {getAgentAvatar(agent)}
                      <Box flex={1}>
                        <Typography 
                          variant="h6"
                          sx={{ 
                            cursor: 'pointer', 
                            '&:hover': { color: 'primary.main', textDecoration: 'underline' } 
                          }}
                          onClick={() => navigate(`/projects/${projectId}/agents/${agentId}`)}
                        >
                          {agent.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {agent.role}
                        </Typography>
                      </Box>
                      {isRunning ? (
                        <CheckCircleIcon color="success" />
                      ) : (
                        <PauseCircleIcon color="disabled" />
                      )}
                    </Box>
                    
                    <Box display="flex" alignItems="center" gap={1} mb={1}>
                      <Typography variant="body2">
                        Status: {isRunning ? 'Running' : 'Stopped'}
                      </Typography>
                      {status?.pid && (
                        <Chip label={`PID: ${status.pid}`} size="small" />
                      )}
                    </Box>
                    
                    {status?.branch && (
                      <Box display="flex" alignItems="center" gap={1} mb={1}>
                        <AccountTreeIcon fontSize="small" color="action" />
                        <Typography variant="body2">
                          {status.branch}
                        </Typography>
                        {status.has_changes && (
                          <Chip label="Uncommitted changes" size="small" color="warning" />
                        )}
                      </Box>
                    )}
                    
                    <Typography variant="caption" color="text.secondary" display="block">
                      Last active: {new Date(agent.last_active).toLocaleDateString()}
                    </Typography>
                  </CardContent>
                  <CardActions>
                    {isRunning ? (
                      <Button
                        size="small"
                        color="error"
                        onClick={async () => {
                          try {
                            await api.post(`/app/projects/${projectId}/agents/${agentId}/stop`);
                            setTimeout(loadAgentStatus, 500);
                          } catch (error) {
                            console.error('Failed to stop agent:', error);
                          }
                        }}
                      >
                        Stop
                      </Button>
                    ) : (
                      <Button
                        size="small"
                        color="success"
                        onClick={async () => {
                          try {
                            await api.post(`/app/projects/${projectId}/agents/${agentId}/start`);
                            setTimeout(loadAgentStatus, 1000);
                          } catch (error) {
                            console.error('Failed to start agent:', error);
                          }
                        }}
                      >
                        Start
                      </Button>
                    )}
                    <Button 
                      size="small"
                      onClick={() => navigate(`/projects/${projectId}/agents/${agentId}`)}
                      startIcon={<SettingsIcon />}
                    >
                      Settings
                    </Button>
                    <Button 
                      size="small"
                      onClick={() => setLogsDialog({ 
                        open: true, 
                        agentId: agentId, 
                        agentName: agent.name 
                      })}
                    >
                      View Logs
                    </Button>
                    <Button 
                      size="small" 
                      color="error"
                      onClick={() => handleRemoveAgent(agentId)}
                    >
                      Remove
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            );
          })}
        </Grid>

        {Object.keys(project.agents).length === 0 && (
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary" gutterBottom>
              No agents configured for this project
            </Typography>
            <Button
              startIcon={<AddIcon />}
              variant="contained"
              onClick={() => setCreateAgentOpen(true)}
              sx={{ mt: 2 }}
            >
              Add First Agent
            </Button>
          </Paper>
        )}
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" mb={2}>Project Configuration</Typography>
              
              <TextField
                fullWidth
                label="Project Name"
                value={projectConfig.name}
                onChange={(e) => setProjectConfig(prev => ({ ...prev, name: e.target.value }))}
                margin="normal"
              />
              
              <TextField
                fullWidth
                label="Project Description"
                value={projectConfig.description}
                onChange={(e) => setProjectConfig(prev => ({ ...prev, description: e.target.value }))}
                margin="normal"
                multiline
                rows={3}
              />
              
              <TextField
                fullWidth
                label="Folder Name"
                value={projectConfig.folder_name}
                onChange={(e) => setProjectConfig(prev => ({ ...prev, folder_name: e.target.value }))}
                margin="normal"
                helperText="Custom folder name for this project (leave empty for auto-generated)"
              />
              
              <Box mt={2}>
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={handleSaveProjectConfig}
                  disabled={savingProject}
                >
                  {savingProject ? 'Saving...' : 'Save Project Details'}
                </Button>
              </Box>
            </Paper>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <TelegramIcon />
                <Typography variant="h6">Telegram Integration</Typography>
              </Box>
              
              <TextField
                fullWidth
                label="Bot Token"
                value={telegramConfig.bot_token}
                onChange={(e) => setTelegramConfig(prev => ({ ...prev, bot_token: e.target.value }))}
                margin="normal"
                type="password"
                helperText="Get from @BotFather on Telegram"
              />
              
              <TextField
                fullWidth
                label="Group/Channel ID"
                value={telegramConfig.group_id}
                onChange={(e) => setTelegramConfig(prev => ({ ...prev, group_id: e.target.value }))}
                margin="normal"
                helperText="The Telegram group where agents will communicate"
              />
              
              <FormControlLabel
                control={
                  <Switch
                    checked={telegramConfig.enabled}
                    onChange={(e) => setTelegramConfig(prev => ({ ...prev, enabled: e.target.checked }))}
                  />
                }
                label="Enable Telegram Bridge"
                sx={{ mt: 2, mb: 2 }}
              />
              
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={handleSaveTelegramConfig}
                disabled={savingTelegram}
              >
                {savingTelegram ? 'Saving...' : 'Save Configuration'}
              </Button>
            </Paper>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <Alert severity="info">
          Agent logs will be displayed here in a future update
        </Alert>
      </TabPanel>

      <CreateAgentDialog
        open={createAgentOpen}
        onClose={() => setCreateAgentOpen(false)}
        onCreate={handleCreateAgent}
      />
      
      <Snackbar
        open={showSaveSuccess}
        autoHideDuration={3000}
        onClose={() => setShowSaveSuccess(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setShowSaveSuccess(false)} severity="success" sx={{ width: '100%' }}>
          Configuration saved successfully!
        </Alert>
      </Snackbar>
      
      {projectId && (
        <AgentLogs
          open={logsDialog.open}
          onClose={() => setLogsDialog({ open: false, agentId: '', agentName: '' })}
          projectId={projectId}
          agentId={logsDialog.agentId}
          agentName={logsDialog.agentName}
        />
      )}
    </Box>
  );
};