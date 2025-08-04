import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert
} from '@mui/material';

interface CreateAgentDialogProps {
  open: boolean;
  onClose: () => void;
  onCreate: (agentData: any) => Promise<void>;
}

const PREDEFINED_ROLES = [
  'backend',
  'frontend',
  'database',
  'qa',
  'ba',
  'teamlead',
  'devops',
  'security'
];

const SUGGESTED_NAMES = {
  backend: ['Alex', 'Blake', 'Cameron', 'Dana'],
  frontend: ['Sarah', 'Taylor', 'Jordan', 'Casey'],
  database: ['Morgan', 'Riley', 'Avery', 'Quinn'],
  qa: ['Pat', 'Sam', 'Charlie', 'Drew'],
  ba: ['Jamie', 'Robin', 'Sydney', 'Reese'],
  teamlead: ['Chris', 'Lee', 'Terry', 'Max'],
  devops: ['Devon', 'Kai', 'Sage', 'River'],
  security: ['Adrian', 'Shay', 'Vale', 'Zion']
};

export const CreateAgentDialog: React.FC<CreateAgentDialogProps> = ({
  open,
  onClose,
  onCreate
}) => {
  const [formData, setFormData] = useState({
    role: '',
    name: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e: any) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Auto-suggest name when role changes
    if (name === 'role' && value && !formData.name) {
      const suggestions = SUGGESTED_NAMES[value as keyof typeof SUGGESTED_NAMES];
      if (suggestions && suggestions.length > 0) {
        setFormData(prev => ({
          ...prev,
          name: suggestions[0]
        }));
      }
    }
  };

  const handleSubmit = async () => {
    setError('');
    setLoading(true);

    try {
      await onCreate(formData);
      
      // Reset form
      setFormData({
        role: '',
        name: ''
      });
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to create agent');
    } finally {
      setLoading(false);
    }
  };

  const getSuggestedNames = () => {
    if (!formData.role) return [];
    return SUGGESTED_NAMES[formData.role as keyof typeof SUGGESTED_NAMES] || [];
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Create New Agent</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={12}>
            <FormControl fullWidth required>
              <InputLabel>Agent Role</InputLabel>
              <Select
                name="role"
                value={formData.role}
                onChange={handleChange}
                label="Agent Role"
              >
                {PREDEFINED_ROLES.map(role => (
                  <MenuItem key={role} value={role}>
                    {role.charAt(0).toUpperCase() + role.slice(1)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Agent Name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              placeholder="Enter agent name"
              helperText={
                formData.role && getSuggestedNames().length > 0
                  ? `Suggestions: ${getSuggestedNames().join(', ')}`
                  : 'Choose a unique name for this agent'
              }
            />
          </Grid>

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
          disabled={loading || !formData.role || !formData.name}
        >
          {loading ? 'Creating...' : 'Create Agent'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};