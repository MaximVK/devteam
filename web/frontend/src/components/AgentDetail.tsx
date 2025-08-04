import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Button,
  IconButton,
  Chip,
  TextField,
  Switch,
  FormControlLabel,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Card,
  CardContent,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Terminal as TerminalIcon,
  Settings as SettingsIcon,
  History as HistoryIcon,
  Code as CodeIcon,
  Folder as FolderIcon,
  Lock as LockIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import api, { appService, AgentConfig as ApiAgentConfig } from '../services/api';

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
      id={`agent-tabpanel-${index}`}
      aria-labelledby={`agent-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

type AgentConfig = ApiAgentConfig;

interface AgentInfo {
  id: string;
  name: string;
  role: string;
  status: string;
  workspace: string;
  last_active: string;
}

export const AgentDetail: React.FC = () => {
  const { projectId, agentId } = useParams<{ projectId: string; agentId: string }>();
  const navigate = useNavigate();
  
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [agent, setAgent] = useState<AgentInfo | null>(null);
  const [config, setConfig] = useState<AgentConfig | null>(null);
  const [originalConfig, setOriginalConfig] = useState<AgentConfig | null>(null);
  const [logs, setLogs] = useState<string>('');
  const [commands, setCommands] = useState<string[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [newPath, setNewPath] = useState('');
  const [newCommand, setNewCommand] = useState('');
  const [newEnvKey, setNewEnvKey] = useState('');
  const [newEnvValue, setNewEnvValue] = useState('');
  const [pathDialog, setPathDialog] = useState(false);
  const [commandDialog, setCommandDialog] = useState(false);
  const [envDialog, setEnvDialog] = useState(false);

  useEffect(() => {
    if (projectId && agentId) {
      loadAgentData();
    }
  }, [projectId, agentId]);

  const loadAgentData = async () => {
    try {
      setLoading(true);
      
      // Load agent info from project
      const projectResponse = await appService.getProject(projectId!);
      const agentInfo = projectResponse.data.agents[agentId!];
      if (agentInfo) {
        setAgent({ id: agentId!, ...agentInfo });
      }
      
      // Load agent configuration
      const configResponse = await appService.getAgentConfig(projectId!, agentId!);
      setConfig(configResponse.data);
      setOriginalConfig(JSON.parse(JSON.stringify(configResponse.data)));
      
      // Load logs
      loadLogs();
      
      // Load commands
      loadCommands();
      
      // Load history if on history tab
      if (tabValue === 3) {
        loadHistory();
      }
    } catch (error) {
      console.error('Failed to load agent data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadLogs = async () => {
    try {
      const response = await appService.getAgentLogs(projectId!, agentId!);
      setLogs(response.data.logs || 'No logs available');
    } catch (error) {
      console.error('Failed to load logs:', error);
      setLogs('Failed to load logs');
    }
  };

  const loadCommands = async () => {
    try {
      const response = await appService.getAgentCommands(projectId!, agentId!);
      setCommands(response.data.commands || []);
    } catch (error) {
      console.error('Failed to load commands:', error);
    }
  };

  const loadHistory = async () => {
    try {
      const response = await api.get(`/agents/${agent?.role}/history`);
      setHistory(response.data.history || []);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    if (newValue === 3 && history.length === 0) {
      loadHistory();
    }
  };

  const handleSaveConfig = async () => {
    if (!config || !projectId || !agentId) return;
    
    try {
      setSaving(true);
      await appService.updateAgentConfig(projectId!, agentId!, config);
      setOriginalConfig(JSON.parse(JSON.stringify(config)));
      // Show success notification
    } catch (error) {
      console.error('Failed to save configuration:', error);
      // Show error notification
    } finally {
      setSaving(false);
    }
  };

  const handleResetConfig = () => {
    if (originalConfig) {
      setConfig(JSON.parse(JSON.stringify(originalConfig)));
    }
  };

  const hasChanges = () => {
    return JSON.stringify(config) !== JSON.stringify(originalConfig);
  };

  const handleAddPath = () => {
    if (newPath && config) {
      const updatedConfig = { ...config };
      if (!updatedConfig.permissions.allowed_paths.includes(newPath)) {
        updatedConfig.permissions.allowed_paths.push(newPath);
        setConfig(updatedConfig);
      }
      setNewPath('');
      setPathDialog(false);
    }
  };

  const handleRemovePath = (index: number) => {
    if (config) {
      const updatedConfig = { ...config };
      updatedConfig.permissions.allowed_paths.splice(index, 1);
      setConfig(updatedConfig);
    }
  };

  const handleAddCommand = () => {
    if (newCommand && config) {
      const updatedConfig = { ...config };
      if (!updatedConfig.permissions.allowed_commands.includes(newCommand)) {
        updatedConfig.permissions.allowed_commands.push(newCommand);
        setConfig(updatedConfig);
      }
      setNewCommand('');
      setCommandDialog(false);
    }
  };

  const handleRemoveCommand = (index: number) => {
    if (config) {
      const updatedConfig = { ...config };
      updatedConfig.permissions.allowed_commands.splice(index, 1);
      setConfig(updatedConfig);
    }
  };

  const handleAddEnvVar = () => {
    if (newEnvKey && newEnvValue && config) {
      const updatedConfig = { ...config };
      updatedConfig.environment[newEnvKey] = newEnvValue;
      setConfig(updatedConfig);
      setNewEnvKey('');
      setNewEnvValue('');
      setEnvDialog(false);
    }
  };

  const handleRemoveEnvVar = (key: string) => {
    if (config) {
      const updatedConfig = { ...config };
      delete updatedConfig.environment[key];
      setConfig(updatedConfig);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!agent || !config) {
    return (
      <Box textAlign="center" py={5}>
        <Typography variant="h6" color="text.secondary">Agent not found</Typography>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(-1)} sx={{ mt: 2 }}>
          Go Back
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <IconButton onClick={() => navigate(`/projects/${projectId}`)}>
          <ArrowBackIcon />
        </IconButton>
        <Box flex={1}>
          <Typography variant="h4">{agent.name}</Typography>
          <Box display="flex" alignItems="center" gap={1} mt={1}>
            <Chip label={agent.role} size="small" color="primary" />
            <Chip 
              label={agent.status} 
              size="small" 
              color={agent.status === 'active' ? 'success' : 'default'}
              icon={agent.status === 'active' ? <CheckCircleIcon /> : <WarningIcon />}
            />
          </Box>
        </Box>
        {hasChanges() && (
          <Box display="flex" gap={1}>
            <Button variant="outlined" onClick={handleResetConfig}>
              Reset
            </Button>
            <Button 
              variant="contained" 
              startIcon={<SaveIcon />}
              onClick={handleSaveConfig}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </Box>
        )}
      </Box>

      {/* Tabs */}
      <Paper sx={{ width: '100%' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="agent detail tabs">
          <Tab label="Settings" icon={<SettingsIcon />} iconPosition="start" />
          <Tab label="Logs" icon={<TerminalIcon />} iconPosition="start" />
          <Tab label="Commands" icon={<CodeIcon />} iconPosition="start" />
          <Tab label="History" icon={<HistoryIcon />} iconPosition="start" />
        </Tabs>

        {/* Settings Tab */}
        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            {/* Basic Settings */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Basic Settings</Typography>
                  
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.settings.enabled}
                        onChange={(e) => setConfig({
                          ...config,
                          settings: { ...config.settings, enabled: e.target.checked }
                        })}
                      />
                    }
                    label="Agent Enabled"
                  />
                  
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.settings.auto_start}
                        onChange={(e) => setConfig({
                          ...config,
                          settings: { ...config.settings, auto_start: e.target.checked }
                        })}
                      />
                    }
                    label="Auto Start with Project"
                  />
                  
                  <Divider sx={{ my: 2 }} />
                  
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel>Claude Model</InputLabel>
                    <Select
                      value={config.settings.model}
                      label="Claude Model"
                      onChange={(e) => setConfig({
                        ...config,
                        settings: { ...config.settings, model: e.target.value }
                      })}
                    >
                      <MenuItem value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</MenuItem>
                      <MenuItem value="claude-3-opus-20240229">Claude 3 Opus</MenuItem>
                      <MenuItem value="claude-3-haiku-20240307">Claude 3 Haiku</MenuItem>
                    </Select>
                  </FormControl>
                  
                  <TextField
                    fullWidth
                    label="Max Tokens"
                    type="number"
                    value={config.settings.max_tokens}
                    onChange={(e) => setConfig({
                      ...config,
                      settings: { ...config.settings, max_tokens: parseInt(e.target.value) || 0 }
                    })}
                    sx={{ mb: 2 }}
                  />
                  
                  <TextField
                    fullWidth
                    label="Temperature"
                    type="number"
                    inputProps={{ step: 0.1, min: 0, max: 1 }}
                    value={config.settings.temperature}
                    onChange={(e) => setConfig({
                      ...config,
                      settings: { ...config.settings, temperature: parseFloat(e.target.value) || 0 }
                    })}
                    sx={{ mb: 2 }}
                  />
                </CardContent>
              </Card>
            </Grid>

            {/* Resource Limits */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Resource Limits</Typography>
                  
                  <TextField
                    fullWidth
                    label="Memory Limit (MB)"
                    type="number"
                    value={config.settings.memory_limit_mb}
                    onChange={(e) => setConfig({
                      ...config,
                      settings: { ...config.settings, memory_limit_mb: parseInt(e.target.value) || 0 }
                    })}
                    sx={{ mb: 2 }}
                  />
                  
                  <TextField
                    fullWidth
                    label="CPU Limit (%)"
                    type="number"
                    inputProps={{ min: 0, max: 100 }}
                    value={config.settings.cpu_limit_percent}
                    onChange={(e) => setConfig({
                      ...config,
                      settings: { ...config.settings, cpu_limit_percent: parseInt(e.target.value) || 0 }
                    })}
                    sx={{ mb: 2 }}
                  />
                  
                  <TextField
                    fullWidth
                    label="Max File Size (MB)"
                    type="number"
                    value={config.permissions.max_file_size_mb}
                    onChange={(e) => setConfig({
                      ...config,
                      permissions: { ...config.permissions, max_file_size_mb: parseInt(e.target.value) || 0 }
                    })}
                    sx={{ mb: 2 }}
                  />
                  
                  <TextField
                    fullWidth
                    label="Max Command Output Lines"
                    type="number"
                    value={config.permissions.max_command_output_lines}
                    onChange={(e) => setConfig({
                      ...config,
                      permissions: { ...config.permissions, max_command_output_lines: parseInt(e.target.value) || 0 }
                    })}
                  />
                </CardContent>
              </Card>
            </Grid>

            {/* Permissions */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Permissions</Typography>
                  
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={4}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={config.permissions.can_access_internet}
                            onChange={(e) => setConfig({
                              ...config,
                              permissions: { ...config.permissions, can_access_internet: e.target.checked }
                            })}
                          />
                        }
                        label="Can Access Internet"
                      />
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={config.permissions.can_install_packages}
                            onChange={(e) => setConfig({
                              ...config,
                              permissions: { ...config.permissions, can_install_packages: e.target.checked }
                            })}
                          />
                        }
                        label="Can Install Packages"
                      />
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={config.permissions.can_modify_git_config}
                            onChange={(e) => setConfig({
                              ...config,
                              permissions: { ...config.permissions, can_modify_git_config: e.target.checked }
                            })}
                          />
                        }
                        label="Can Modify Git Config"
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            {/* Allowed Paths */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6">Allowed Paths</Typography>
                    <IconButton color="primary" onClick={() => setPathDialog(true)}>
                      <AddIcon />
                    </IconButton>
                  </Box>
                  
                  <List dense>
                    {config.permissions.allowed_paths.map((path, index) => (
                      <ListItem key={index} secondaryAction={
                        <IconButton edge="end" onClick={() => handleRemovePath(index)}>
                          <DeleteIcon />
                        </IconButton>
                      }>
                        <ListItemIcon>
                          <FolderIcon />
                        </ListItemIcon>
                        <ListItemText primary={path} />
                      </ListItem>
                    ))}
                    {config.permissions.allowed_paths.length === 0 && (
                      <ListItem>
                        <ListItemText 
                          primary="No additional paths allowed" 
                          secondary="Agent can only access its workspace"
                        />
                      </ListItem>
                    )}
                  </List>
                </CardContent>
              </Card>
            </Grid>

            {/* Allowed Commands */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6">Allowed Commands</Typography>
                    <IconButton color="primary" onClick={() => setCommandDialog(true)}>
                      <AddIcon />
                    </IconButton>
                  </Box>
                  
                  <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                    <List dense>
                      {config.permissions.allowed_commands.map((command, index) => (
                        <ListItem key={index} secondaryAction={
                          <IconButton edge="end" onClick={() => handleRemoveCommand(index)}>
                            <DeleteIcon />
                          </IconButton>
                        }>
                          <ListItemIcon>
                            <TerminalIcon />
                          </ListItemIcon>
                          <ListItemText primary={command} />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Environment Variables */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6">Environment Variables</Typography>
                    <IconButton color="primary" onClick={() => setEnvDialog(true)}>
                      <AddIcon />
                    </IconButton>
                  </Box>
                  
                  <List dense>
                    {Object.entries(config.environment).map(([key, value]) => (
                      <ListItem key={key} secondaryAction={
                        <IconButton edge="end" onClick={() => handleRemoveEnvVar(key)}>
                          <DeleteIcon />
                        </IconButton>
                      }>
                        <ListItemIcon>
                          <LockIcon />
                        </ListItemIcon>
                        <ListItemText 
                          primary={key}
                          secondary={value}
                        />
                      </ListItem>
                    ))}
                    {Object.keys(config.environment).length === 0 && (
                      <ListItem>
                        <ListItemText 
                          primary="No custom environment variables" 
                          secondary="Add environment variables for the agent"
                        />
                      </ListItem>
                    )}
                  </List>
                </CardContent>
              </Card>
            </Grid>

            {/* System Prompt Additions */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>System Prompt Additions</Typography>
                  <TextField
                    fullWidth
                    multiline
                    rows={4}
                    label="Additional instructions for the agent"
                    value={config.settings.system_prompt_additions}
                    onChange={(e) => setConfig({
                      ...config,
                      settings: { ...config.settings, system_prompt_additions: e.target.value }
                    })}
                    helperText="These instructions will be added to the agent's system prompt"
                  />
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Logs Tab */}
        <TabPanel value={tabValue} index={1}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Agent Logs</Typography>
            <Button startIcon={<RefreshIcon />} onClick={loadLogs}>
              Refresh
            </Button>
          </Box>
          <Paper sx={{ p: 2, bgcolor: '#1e1e1e', color: '#fff', fontFamily: 'monospace', fontSize: 12, overflow: 'auto', maxHeight: 600 }}>
            <pre style={{ margin: 0 }}>{logs}</pre>
          </Paper>
        </TabPanel>

        {/* Commands Tab */}
        <TabPanel value={tabValue} index={2}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Recent Commands</Typography>
            <Button startIcon={<RefreshIcon />} onClick={loadCommands}>
              Refresh
            </Button>
          </Box>
          <List>
            {commands.map((command, index) => (
              <ListItem key={index}>
                <ListItemIcon>
                  <TerminalIcon />
                </ListItemIcon>
                <ListItemText 
                  primary={command}
                  primaryTypographyProps={{ fontFamily: 'monospace', fontSize: 14 }}
                />
              </ListItem>
            ))}
            {commands.length === 0 && (
              <ListItem>
                <ListItemText 
                  primary="No commands executed yet" 
                  secondary="Commands executed by the agent will appear here"
                />
              </ListItem>
            )}
          </List>
        </TabPanel>

        {/* History Tab */}
        <TabPanel value={tabValue} index={3}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Conversation History</Typography>
            <Button startIcon={<RefreshIcon />} onClick={loadHistory}>
              Refresh
            </Button>
          </Box>
          <List>
            {history.map((message, index) => (
              <ListItem key={index} alignItems="flex-start">
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Chip 
                        label={message.role} 
                        size="small" 
                        color={message.role === 'user' ? 'primary' : 'default'}
                      />
                      <Typography variant="caption" color="text.secondary">
                        {new Date(message.timestamp).toLocaleString()}
                      </Typography>
                    </Box>
                  }
                  secondary={
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      {message.content}
                    </Typography>
                  }
                />
              </ListItem>
            ))}
            {history.length === 0 && (
              <ListItem>
                <ListItemText 
                  primary="No conversation history" 
                  secondary="Agent conversations will appear here"
                />
              </ListItem>
            )}
          </List>
        </TabPanel>
      </Paper>

      {/* Dialogs */}
      <Dialog open={pathDialog} onClose={() => setPathDialog(false)}>
        <DialogTitle>Add Allowed Path</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Path"
            value={newPath}
            onChange={(e) => setNewPath(e.target.value)}
            placeholder="/path/to/directory"
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPathDialog(false)}>Cancel</Button>
          <Button onClick={handleAddPath} variant="contained">Add</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={commandDialog} onClose={() => setCommandDialog(false)}>
        <DialogTitle>Add Allowed Command</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Command"
            value={newCommand}
            onChange={(e) => setNewCommand(e.target.value)}
            placeholder="command-name"
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCommandDialog(false)}>Cancel</Button>
          <Button onClick={handleAddCommand} variant="contained">Add</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={envDialog} onClose={() => setEnvDialog(false)}>
        <DialogTitle>Add Environment Variable</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Key"
            value={newEnvKey}
            onChange={(e) => setNewEnvKey(e.target.value)}
            placeholder="VARIABLE_NAME"
            sx={{ mt: 1, mb: 2 }}
          />
          <TextField
            fullWidth
            label="Value"
            value={newEnvValue}
            onChange={(e) => setNewEnvValue(e.target.value)}
            placeholder="value"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEnvDialog(false)}>Cancel</Button>
          <Button onClick={handleAddEnvVar} variant="contained">Add</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};