#==============================================================================
# Variables for Dapmeet Infrastructure
#==============================================================================

#------------------------------------------------------------------------------
# Yandex Cloud Authentication
#------------------------------------------------------------------------------

variable "yc_token" {
  description = "Yandex Cloud OAuth token"
  type        = string
  sensitive   = true
}

variable "yc_cloud_id" {
  description = "Yandex Cloud ID"
  type        = string
}

variable "yc_folder_id" {
  description = "Yandex Cloud Folder ID"
  type        = string
}

variable "yc_zone" {
  description = "Yandex Cloud availability zone"
  type        = string
  default     = "ru-central1-a"
}

#------------------------------------------------------------------------------
# Project Configuration
#------------------------------------------------------------------------------

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "dapmeet"
}

variable "environment" {
  description = "Environment (dev, staging, production)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "timezone" {
  description = "Server timezone"
  type        = string
  default     = "Asia/Almaty"
}

#------------------------------------------------------------------------------
# Network Configuration
#------------------------------------------------------------------------------

variable "subnet_cidr" {
  description = "CIDR block for the subnet"
  type        = string
  default     = "10.128.0.0/24"
}

variable "ssh_allowed_ips" {
  description = "List of IP addresses allowed to SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Restrict in production!
}

variable "reserve_static_ip" {
  description = "Reserve static IP addresses for VMs"
  type        = bool
  default     = false
}

#------------------------------------------------------------------------------
# VM Configuration - Frontend
#------------------------------------------------------------------------------

variable "frontend_cores" {
  description = "Number of CPU cores for frontend VM"
  type        = number
  default     = 2
}

variable "frontend_memory" {
  description = "RAM in GB for frontend VM"
  type        = number
  default     = 2
}

#------------------------------------------------------------------------------
# VM Configuration - Backend
#------------------------------------------------------------------------------

variable "backend_cores" {
  description = "Number of CPU cores for backend VM"
  type        = number
  default     = 2
}

variable "backend_memory" {
  description = "RAM in GB for backend VM"
  type        = number
  default     = 4
}

#------------------------------------------------------------------------------
# VM Common Configuration
#------------------------------------------------------------------------------

variable "vm_platform_id" {
  description = "Yandex Compute platform ID"
  type        = string
  default     = "standard-v3"
}

variable "vm_core_fraction" {
  description = "Guaranteed CPU core fraction (5, 20, 50, 100)"
  type        = number
  default     = 20
  
  validation {
    condition     = contains([5, 20, 50, 100], var.vm_core_fraction)
    error_message = "Core fraction must be 5, 20, 50, or 100."
  }
}

variable "vm_disk_size" {
  description = "Boot disk size in GB"
  type        = number
  default     = 20
}

variable "use_preemptible" {
  description = "Use preemptible (spot) instances for cost savings"
  type        = bool
  default     = true
}

#------------------------------------------------------------------------------
# SSH Configuration
#------------------------------------------------------------------------------

variable "ssh_user" {
  description = "SSH username for VMs"
  type        = string
  default     = "automation"
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key file"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

#------------------------------------------------------------------------------
# Database Configuration
#------------------------------------------------------------------------------

variable "db_password" {
  description = "PostgreSQL database password"
  type        = string
  sensitive   = true
  default     = "ChangeMeInProduction!"
}

#------------------------------------------------------------------------------
# DNS Configuration (Optional)
#------------------------------------------------------------------------------

variable "create_dns_records" {
  description = "Create DNS records in Yandex DNS"
  type        = bool
  default     = false
}

variable "dns_zone_id" {
  description = "Yandex DNS zone ID"
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "dapmeet.local"
}

