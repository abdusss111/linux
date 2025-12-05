# Bonus Task 1: CI/CD Integration with GitHub Actions

This bonus task integrates the SIS5 Ansible playbooks with GitHub Actions for automated deployment.

## Overview

The CI/CD pipeline automates:
1. **Linting** - YAML and Ansible syntax validation
2. **Syntax Check** - Playbook syntax verification
3. **Deployment** - Automated Ansible playbook execution
4. **Verification** - Post-deployment health checks

## Files Structure

```
bonus1-cicd/
├── .github/
│   └── workflows/
│       ├── ansible-deploy.yml      # Main deployment workflow
│       └── ansible-scheduled.yml   # Scheduled maintenance workflow
├── .yamllint.yml                   # YAML lint configuration
├── verify-playbook.yml             # Verification playbook
└── README.md                       # This file
```

## Setup Instructions

### 1. GitHub Repository Secrets

Configure these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

| Secret Name | Description |
|-------------|-------------|
| `ANSIBLE_SSH_PRIVATE_KEY` | Private SSH key for automation user |
| `VM1_HOST` | IP address of VM1 (frontend) |
| `VM2_HOST` | IP address of VM2 (backend) |
| `ANSIBLE_USER` | Username for SSH (usually `automation`) |
| `ANSIBLE_BECOME_PASSWORD` | Sudo password (if required) |

### 2. Copy Workflow Files

Copy the `.github` directory to your repository root:

```bash
cp -r .github /path/to/your/repo/
```

### 3. Generate SSH Key (if not exists)

```bash
# Generate new SSH key for CI/CD
ssh-keygen -t ed25519 -C "github-actions@dapmeet" -f ~/.ssh/github_actions_key -N ""

# Copy public key to VMs
ssh-copy-id -i ~/.ssh/github_actions_key.pub automation@VM1_IP
ssh-copy-id -i ~/.ssh/github_actions_key.pub automation@VM2_IP

# Add private key content to GitHub secret ANSIBLE_SSH_PRIVATE_KEY
cat ~/.ssh/github_actions_key
```

## Usage

### Automatic Deployment

Push changes to the `main` branch under `sis5/ansible/`:
```bash
git add sis5/ansible/
git commit -m "Update Ansible configuration"
git push origin main
```

### Manual Deployment

1. Go to Actions tab in GitHub
2. Select "Deploy Dapmeet Infrastructure"
3. Click "Run workflow"
4. Choose:
   - **Environment**: staging or production
   - **Playbook**: site.yml, vm1.yml, or vm2.yml
   - **Tags**: Optional, comma-separated (e.g., `docker,services`)

### Scheduled Maintenance

Runs automatically every Sunday at 2 AM UTC, or trigger manually:
1. Go to Actions → "Scheduled Maintenance"
2. Select maintenance task:
   - `security-updates` - Apply system updates
   - `backup-verification` - Check backup status
   - `health-check` - Verify services
   - `log-rotation` - Force log rotation

## Pipeline Stages

```
┌─────────┐    ┌──────────────┐    ┌─────────┐    ┌────────┐
│  Lint   │ -> │ Syntax Check │ -> │ Deploy  │ -> │ Notify │
└─────────┘    └──────────────┘    └─────────┘    └────────┘
```

### Stage Details

1. **Lint**
   - Runs `yamllint` on all YAML files
   - Runs `ansible-lint` on playbooks
   - Non-blocking (warnings only)

2. **Syntax Check**
   - Validates playbook syntax with `--syntax-check`
   - Blocks deployment if syntax errors exist

3. **Deploy**
   - Only runs on `main` branch or manual trigger
   - Creates dynamic inventory from secrets
   - Executes selected Ansible playbook
   - Uploads logs as artifacts

4. **Notify**
   - Reports deployment status
   - Can be extended for Slack/Email notifications

## Example: Full Deployment

```yaml
# Trigger via workflow_dispatch
environment: production
playbook: site.yml
tags: ""  # Run all tags
```

This runs:
```bash
ansible-playbook -i inventory/dynamic-hosts.yml playbooks/site.yml -v
```

## Example: Deploy Only Docker Updates

```yaml
environment: staging
playbook: site.yml
tags: sis4,docker
```

This runs:
```bash
ansible-playbook -i inventory/dynamic-hosts.yml playbooks/site.yml --tags sis4,docker -v
```

## Troubleshooting

### SSH Connection Failed
- Verify `ANSIBLE_SSH_PRIVATE_KEY` secret is correctly formatted
- Ensure VM IPs are correct in secrets
- Check that automation user exists and has SSH access

### Playbook Failed
- Check "ansible-logs" artifact for detailed output
- Verify inventory variables are correct
- Test playbook locally first

### Permission Denied
- Ensure automation user has sudo privileges
- Check `ANSIBLE_BECOME_PASSWORD` if using become

## Security Considerations

1. Use environment protection rules for production
2. Require approval for production deployments
3. Rotate SSH keys periodically
4. Use secrets for all sensitive data
5. Review audit logs regularly

## Integration with SIS5

This CI/CD pipeline executes the same playbooks from SIS5:

| SIS5 Role | CI/CD Tag | Description |
|-----------|-----------|-------------|
| users | `sis2,users` | User creation |
| permissions | `sis2,permissions` | Permission setup |
| ssh | `sis2,ssh` | SSH configuration |
| firewall | `sis3,firewall` | Firewall rules |
| docker | `sis4,docker` | Docker installation |
| services | `sis4,services` | Systemd services |
| cron | `sis4,cron` | Scheduled tasks |

