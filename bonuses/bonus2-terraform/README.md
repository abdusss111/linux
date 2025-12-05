# Bonus Task 2: Terraform Infrastructure as Code

This bonus task creates the VM infrastructure for Dapmeet on Yandex Cloud using Terraform.

## Overview

This Terraform configuration provisions:
- **VPC Network** - Isolated network for Dapmeet
- **Security Groups** - Firewall rules for frontend and backend
- **VM1 (Frontend)** - Next.js application server
- **VM2 (Backend)** - FastAPI + PostgreSQL server

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Yandex Cloud                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  VPC: dapmeet-network                     │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              Subnet: 10.128.0.0/24                  │  │  │
│  │  │                                                     │  │  │
│  │  │  ┌─────────────────┐    ┌─────────────────┐        │  │  │
│  │  │  │   VM1-Frontend  │    │   VM2-Backend   │        │  │  │
│  │  │  │   ───────────   │    │   ───────────   │        │  │  │
│  │  │  │   • Next.js     │    │   • FastAPI     │        │  │  │
│  │  │  │   • Nginx       │───▶│   • PostgreSQL  │        │  │  │
│  │  │  │   • Docker      │    │   • Docker      │        │  │  │
│  │  │  │                 │    │                 │        │  │  │
│  │  │  │   Ports:        │    │   Ports:        │        │  │  │
│  │  │  │   22,80,443,3000│    │   22,8000,5432  │        │  │  │
│  │  │  └─────────────────┘    └─────────────────┘        │  │  │
│  │  │                                                     │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Yandex Cloud Account** - [Create account](https://cloud.yandex.com/)
2. **Yandex Cloud CLI** - [Installation guide](https://cloud.yandex.com/docs/cli/quickstart)
3. **Terraform** >= 1.5.0 - [Installation guide](https://developer.hashicorp.com/terraform/install)
4. **SSH Key Pair** - For VM access

## Quick Start

### 1. Install Yandex Cloud CLI

```bash
# macOS
brew install yandex-cloud-cli

# Linux
curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
```

### 2. Configure Yandex Cloud CLI

```bash
# Initialize CLI and login
yc init

# Get your OAuth token
yc config get token

# Get cloud and folder IDs
yc resource-manager cloud list
yc resource-manager folder list
```

### 3. Generate SSH Key (if needed)

```bash
ssh-keygen -t rsa -b 4096 -C "dapmeet@terraform" -f ~/.ssh/dapmeet_key
```

### 4. Configure Terraform Variables

```bash
# Copy example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
vim terraform.tfvars
```

### 5. Initialize Terraform

```bash
terraform init
```

### 6. Preview Changes

```bash
terraform plan
```

### 7. Create Infrastructure

```bash
terraform apply
```

### 8. Get Output Information

```bash
# Show all outputs
terraform output

# Get SSH commands
terraform output ssh_frontend
terraform output ssh_backend

# Get Ansible inventory
terraform output ansible_inventory > ../sis5/ansible/inventory/hosts.yml
```

## File Structure

```
bonus2-terraform/
├── main.tf                    # Main Terraform configuration
├── variables.tf               # Variable definitions
├── outputs.tf                 # Output definitions
├── terraform.tfvars.example   # Example variables (copy to terraform.tfvars)
├── cloud-init/
│   ├── frontend.yaml          # Cloud-init for VM1
│   └── backend.yaml           # Cloud-init for VM2
└── README.md                  # This file
```

## Configuration Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `yc_token` | Yandex Cloud OAuth token | - |
| `yc_cloud_id` | Cloud ID | - |
| `yc_folder_id` | Folder ID | - |
| `yc_zone` | Availability zone | ru-central1-a |
| `project_name` | Project name | dapmeet |
| `environment` | Environment (dev/staging/production) | dev |
| `frontend_cores` | CPU cores for frontend | 2 |
| `frontend_memory` | RAM for frontend (GB) | 2 |
| `backend_cores` | CPU cores for backend | 2 |
| `backend_memory` | RAM for backend (GB) | 4 |
| `use_preemptible` | Use spot instances | true |
| `ssh_user` | SSH username | automation |
| `db_password` | PostgreSQL password | - |

## Usage Examples

### Create Development Environment

```bash
terraform apply -var="environment=dev" -var="use_preemptible=true"
```

### Create Production Environment

```bash
terraform apply \
  -var="environment=production" \
  -var="use_preemptible=false" \
  -var="frontend_cores=4" \
  -var="frontend_memory=4" \
  -var="backend_cores=4" \
  -var="backend_memory=8"
```

### Destroy Infrastructure

```bash
terraform destroy
```

### Update Specific Resources

```bash
# Only update frontend VM
terraform apply -target=yandex_compute_instance.vm1_frontend

# Only update security groups
terraform apply -target=yandex_vpc_security_group.frontend_sg
```

## Integration with SIS5 Ansible

After Terraform creates the VMs:

1. Get the generated Ansible inventory:
```bash
terraform output -raw ansible_inventory > ../sis5/ansible/inventory/hosts.yml
```

2. Run the Ansible playbook:
```bash
cd ../sis5/ansible
ansible-playbook -i inventory/hosts.yml playbooks/site.yml
```

## Cost Optimization

| Feature | Savings | Setting |
|---------|---------|---------|
| Preemptible instances | Up to 70% | `use_preemptible = true` |
| Lower core fraction | 20-50% | `vm_core_fraction = 20` |
| Right-size VMs | Variable | Adjust `*_cores` and `*_memory` |

**Estimated Monthly Costs (ru-central1-a, preemptible):**
- VM1 (2 cores, 2GB): ~$5-8/month
- VM2 (2 cores, 4GB): ~$8-12/month
- Network/Storage: ~$2-5/month
- **Total: ~$15-25/month**

## Troubleshooting

### Authentication Error
```bash
# Refresh token
yc init
yc config get token
# Update terraform.tfvars with new token
```

### Quota Exceeded
```bash
# Check quotas
yc resource-manager folder list-access-bindings --id <folder-id>
# Request quota increase in Yandex Cloud Console
```

### SSH Connection Failed
```bash
# Check VM status
yc compute instance list

# Check if VM is ready (cloud-init complete)
ssh automation@<ip> "cat /var/log/cloud-init-complete.log"
```

### Resource Already Exists
```bash
# Import existing resource
terraform import yandex_compute_instance.vm1_frontend <instance-id>
```

## Security Recommendations

1. **Restrict SSH access** - Set `ssh_allowed_ips` to your IP only
2. **Use strong passwords** - Set secure `db_password`
3. **Enable monitoring** - Add Yandex Monitoring integration
4. **Regular backups** - Configure automated PostgreSQL backups
5. **Update regularly** - Cloud-init updates packages on creation

## State Management

For team environments, use remote state:

```hcl
terraform {
  backend "s3" {
    endpoint   = "storage.yandexcloud.net"
    bucket     = "dapmeet-terraform-state"
    key        = "infrastructure/terraform.tfstate"
    region     = "ru-central1"
    
    skip_region_validation      = true
    skip_credentials_validation = true
  }
}
```

Create the bucket:
```bash
yc storage bucket create --name dapmeet-terraform-state
```

## Links

- [Yandex Cloud Documentation](https://cloud.yandex.com/docs)
- [Terraform Yandex Provider](https://registry.terraform.io/providers/yandex-cloud/yandex/latest/docs)
- [Cloud-init Documentation](https://cloudinit.readthedocs.io/)

