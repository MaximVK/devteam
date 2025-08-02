import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Grid,
  List,
  ListItem,
  ListItemText,
  Divider,
  Chip
} from '@mui/material';
import { api } from '../services/api';

interface WorkspaceStatus {
  initialized: boolean;
  working_folder?: string;
  maestro_exists: boolean;
  available_roles: string[];
  active_agents: Record<string, any>;
}

interface SetupFormData {
  working_folder: string;
  repository_url: string;
  base_branch: string;
  anthropic_api_key: string;
  github_token: string;
  telegram_bot_token: string;
  telegram_channel_id: string;
  git_user_name: string;
  git_user_email: string;
}

export const WorkspaceSetup: React.FC = () => {
  const [status, setStatus] = useState<WorkspaceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [setupForm, setSetupForm] = useState<SetupFormData>({
    working_folder: `${process.env.HOME || '/home/user'}/devteam-workspace`,
    repository_url: '',
    base_branch: 'main-agents',
    anthropic_api_key: '',
    github_token: '',
    telegram_bot_token: '',
    telegram_channel_id: '',
    git_user_name: 'DevTeam Agents',
    git_user_email: 'agents@devteam.local'
  });
  const [setupError, setSetupError] = useState<string>('');
  const [setupSuccess, setSetupSuccess] = useState(false);

  useEffect(() => {
    checkWorkspaceStatus();
  }, []);

  const checkWorkspaceStatus = async () => {
    try {
      const response = await api.get('/workspace/status');
      setStatus(response.data);
    } catch (error: any) {
      console.error('Failed to check workspace status:', error);
      // If it's a 404, the endpoint might not exist yet
      if (error.response?.status === 404) {
        setStatus({ initialized: false, available_roles: [], active_agents: {}, maestro_exists: false });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSetupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSetupError('');
    setLoading(true);

    try {
      await api.post('/workspace/initialize', setupForm);
      setSetupSuccess(true);
      await checkWorkspaceStatus();
    } catch (error: any) {
      setSetupError(error.response?.data?.detail || 'Failed to initialize workspace');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setSetupForm(prev => ({
      ...prev,
      [name]: value
    }));
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography ml={2}>Checking workspace status...</Typography>
      </Box>
    );
  }

  if (status?.initialized) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>Workspace Status</Typography>
        
        <Alert severity="success" sx={{ mb: 3 }}>
          Workspace is initialized at: {status.working_folder}
        </Alert>
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>Available Roles</Typography>
            <List>
              {status.available_roles.map(role => (
                <ListItem key={role}>
                  <ListItemText primary={role} />
                </ListItem>
              ))}
            </List>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>Active Agents</Typography>
            {Object.keys(status.active_agents).length > 0 ? (
              <List>
                {Object.entries(status.active_agents).map(([role, info]) => (
                  <ListItem key={role}>
                    <ListItemText 
                      primary={role}
                      secondary={`Status: ${info.status}`}
                    />
                    <Chip 
                      label={info.status} 
                      color={info.status === 'active' ? 'success' : 'default'}
                      size="small"
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography color="text.secondary">No active agents</Typography>
            )}
          </Grid>
        </Grid>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom>Initialize DevTeam Workspace</Typography>
      
      {setupSuccess ? (
        <Alert severity="success" sx={{ mb: 2 }}>
          Workspace initialized successfully! 
          <Button size="small" onClick={() => window.location.reload()}>
            Refresh to continue
          </Button>
        </Alert>
      ) : (
        <form onSubmit={handleSetupSubmit}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Working Folder"
                name="working_folder"
                value={setupForm.working_folder}
                onChange={handleInputChange}
                required
                helperText="Base directory for all workspaces"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Repository URL"
                name="repository_url"
                value={setupForm.repository_url}
                onChange={handleInputChange}
                required
                placeholder="https://github.com/username/repo.git"
                helperText="Git repository to clone"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Base Branch for Agents"
                name="base_branch"
                value={setupForm.base_branch}
                onChange={handleInputChange}
                required
                helperText="Branch that agents will create feature branches from"
              />
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6" gutterBottom>API Keys</Typography>
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Anthropic API Key"
                name="anthropic_api_key"
                type="password"
                value={setupForm.anthropic_api_key}
                onChange={handleInputChange}
                required
                helperText="Required for AI agents"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="GitHub Token"
                name="github_token"
                type="password"
                value={setupForm.github_token}
                onChange={handleInputChange}
                helperText="Optional: For GitHub integration"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Telegram Bot Token"
                name="telegram_bot_token"
                type="password"
                value={setupForm.telegram_bot_token}
                onChange={handleInputChange}
                helperText="Optional: For Telegram integration"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Telegram Channel ID"
                name="telegram_channel_id"
                value={setupForm.telegram_channel_id}
                onChange={handleInputChange}
                helperText="Optional: Channel ID for Telegram notifications"
              />
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6" gutterBottom>Git Configuration</Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Git User Name"
                name="git_user_name"
                value={setupForm.git_user_name}
                onChange={handleInputChange}
                required
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Git User Email"
                name="git_user_email"
                type="email"
                value={setupForm.git_user_email}
                onChange={handleInputChange}
                required
              />
            </Grid>

            {setupError && (
              <Grid item xs={12}>
                <Alert severity="error">{setupError}</Alert>
              </Grid>
            )}

            <Grid item xs={12}>
              <Button
                type="submit"
                variant="contained"
                size="large"
                fullWidth
                disabled={loading}
              >
                {loading ? 'Initializing...' : 'Initialize Workspace'}
              </Button>
            </Grid>
          </Grid>
        </form>
      )}
    </Paper>
  );
};