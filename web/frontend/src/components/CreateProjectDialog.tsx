import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Grid,
  FormControlLabel,
  Checkbox,
  Chip,
  Box,
  Typography,
  Alert
} from '@mui/material';
import api from '../services/api';

interface CreateProjectDialogProps {
  open: boolean;
  onClose: () => void;
  onCreate: (projectData: any) => Promise<void>;
}

interface ProjectFormData {
  project_name: string;
  repository_url: string;
  description: string;
  base_branch: string;
  override_git_config: boolean;
  git_user_name: string;
  git_user_email: string;
  initial_agents: Array<{ role: string; name: string }>;
}

export const CreateProjectDialog: React.FC<CreateProjectDialogProps> = ({
  open,
  onClose,
  onCreate
}) => {
  const [formData, setFormData] = useState<ProjectFormData>({
    project_name: '',
    repository_url: '',
    description: '',
    base_branch: 'main-agents',
    override_git_config: false,
    git_user_name: '',
    git_user_email: '',
    initial_agents: []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: e.target.type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async () => {
    setError('');
    setLoading(true);

    try {
      await onCreate({
        ...formData,
        initial_agents: []
      });

      // Reset form
      setFormData({
        project_name: '',
        repository_url: '',
        description: '',
        base_branch: 'main-agents',
        override_git_config: false,
        git_user_name: '',
        git_user_email: '',
        initial_agents: []
      });
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Create New Project</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Project Name"
              name="project_name"
              value={formData.project_name}
              onChange={handleChange}
              required
              placeholder="E-commerce Platform"
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Repository URL"
              name="repository_url"
              value={formData.repository_url}
              onChange={handleChange}
              required
              placeholder="https://github.com/company/project.git"
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              multiline
              rows={2}
              label="Description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              placeholder="Brief description of the project"
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Base Branch for Agents"
              name="base_branch"
              value={formData.base_branch}
              onChange={handleChange}
              required
              helperText="Branch that agents will create feature branches from"
            />
          </Grid>

          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.override_git_config}
                  onChange={handleChange}
                  name="override_git_config"
                />
              }
              label="Override Git Configuration"
            />
          </Grid>

          {formData.override_git_config && (
            <>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Git User Name"
                  name="git_user_name"
                  value={formData.git_user_name}
                  onChange={handleChange}
                  required={formData.override_git_config}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Git User Email"
                  name="git_user_email"
                  value={formData.git_user_email}
                  onChange={handleChange}
                  type="email"
                  required={formData.override_git_config}
                />
              </Grid>
            </>
          )}

          {error && (
            <Grid item xs={12}>
              <Alert severity="error">{error}</Alert>
            </Grid>
          )}
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button 
          onClick={handleSubmit} 
          variant="contained"
          disabled={loading || !formData.project_name || !formData.repository_url}
        >
          {loading ? 'Creating...' : 'Create Project'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};