import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  Snackbar,
  CircularProgress
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import FolderIcon from '@mui/icons-material/Folder';
import api from '../services/api';

interface AppConfig {
  version: string;
  home_directory: string;
  primary_folder: string | null;
  tokens: {
    anthropic_api_key?: string;
    github_token?: string;
    telegram_bot_token?: string;
    telegram_channel_id?: string;
  };
  global_settings: any;
  predefined_roles: string[];
  project_count: number;
}

export const AppSettings: React.FC = () => {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    home_directory: '',
    primary_folder: '',
    anthropic_api_key: '',
    github_token: '',
    telegram_bot_token: '',
    telegram_channel_id: ''
  });
  const [showSuccess, setShowSuccess] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await api.get('/app/config');
      setConfig(response.data);
      setFormData({
        home_directory: response.data.home_directory || '',
        primary_folder: response.data.primary_folder || '',
        anthropic_api_key: response.data.tokens?.anthropic_api_key || '',
        github_token: response.data.tokens?.github_token || '',
        telegram_bot_token: response.data.tokens?.telegram_bot_token || '',
        telegram_channel_id: response.data.tokens?.telegram_channel_id || ''
      });
    } catch (error) {
      console.error('Failed to load app config:', error);
      setError('Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    
    try {
      await api.put('/app/config', {
        home_directory: formData.home_directory,
        primary_folder: formData.primary_folder || null,
        anthropic_api_key: formData.anthropic_api_key,
        github_token: formData.github_token || null,
        telegram_bot_token: formData.telegram_bot_token || null,
        telegram_channel_id: formData.telegram_channel_id || null
      });
      await loadConfig();
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 3000);
    } catch (error) {
      console.error('Failed to save app config:', error);
      setError('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!config) {
    return (
      <Alert severity="error">Failed to load application configuration</Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Application Settings
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          API Configuration
        </Typography>
        
        <TextField
          fullWidth
          label="Anthropic API Key"
          type="password"
          value={formData.anthropic_api_key}
          onChange={(e) => setFormData({ ...formData, anthropic_api_key: e.target.value })}
          margin="normal"
          helperText="Required for AI-powered features"
          required
        />
        
        <TextField
          fullWidth
          label="GitHub Token"
          type="password"
          value={formData.github_token}
          onChange={(e) => setFormData({ ...formData, github_token: e.target.value })}
          margin="normal"
          helperText="Personal access token for GitHub integration (optional)"
        />
      </Paper>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          <FolderIcon />
          <Typography variant="h6">Directory Configuration</Typography>
        </Box>

        <TextField
          fullWidth
          label="Home Directory"
          value={formData.home_directory}
          onChange={(e) => setFormData({ ...formData, home_directory: e.target.value })}
          margin="normal"
          helperText="Base directory for DevTeam configuration and data"
          required
        />

        <TextField
          fullWidth
          label="Projects Directory Override"
          value={formData.primary_folder}
          onChange={(e) => setFormData({ ...formData, primary_folder: e.target.value })}
          margin="normal"
          helperText="Custom location for all projects (optional - leave empty to use home_directory/projects)"
          placeholder={`${formData.home_directory}/projects`}
        />
      </Paper>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Telegram Integration (Optional)
        </Typography>
        
        <TextField
          fullWidth
          label="Telegram Bot Token"
          value={formData.telegram_bot_token}
          onChange={(e) => setFormData({ ...formData, telegram_bot_token: e.target.value })}
          margin="normal"
          helperText="Create a bot via @BotFather on Telegram"
        />
        
        <TextField
          fullWidth
          label="Telegram Channel ID"
          value={formData.telegram_channel_id}
          onChange={(e) => setFormData({ ...formData, telegram_channel_id: e.target.value })}
          margin="normal"
          helperText="Channel or group ID for notifications"
        />
      </Paper>

      <Box mt={3} mb={3}>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSave}
          disabled={saving || !formData.anthropic_api_key || !formData.home_directory}
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </Button>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          System Information
        </Typography>
        
        <Typography variant="body2" color="text.secondary">
          Version: {config.version}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Total Projects: {config.project_count}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Current Projects Directory: {formData.primary_folder || `${formData.home_directory}/projects`}
        </Typography>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}

      <Snackbar
        open={showSuccess}
        autoHideDuration={3000}
        onClose={() => setShowSuccess(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setShowSuccess(false)} severity="success" sx={{ width: '100%' }}>
          Settings saved successfully!
        </Alert>
      </Snackbar>
    </Box>
  );
};