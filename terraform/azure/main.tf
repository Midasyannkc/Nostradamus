# Azure landing zone for the streaming side. Design only: it has been validated with `terraform validate`
# patterns in CI but never applied to a live subscription.
terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
  }
}

provider "azurerm" {
  features {}
}

variable "location" {
  type    = string
  default = "southcentralus"
}

resource "azurerm_resource_group" "nostradamus" {
  name     = "rg-nostradamus"
  location = var.location
}

# Kafka-compatible event stream: 4 partitions per hub, matching the NostraLog partition count.
resource "azurerm_eventhub_namespace" "events" {
  name                = "evhns-nostradamus"
  location            = azurerm_resource_group.nostradamus.location
  resource_group_name = azurerm_resource_group.nostradamus.name
  sku                 = "Standard"
  capacity            = 1
}

resource "azurerm_eventhub" "borrower_events" {
  name              = "borrower-events"
  namespace_id      = azurerm_eventhub_namespace.events.id
  partition_count   = 4
  message_retention = 7
}

resource "azurerm_eventhub" "dead_letter" {
  name              = "borrower-events-dead-letter"
  namespace_id      = azurerm_eventhub_namespace.events.id
  partition_count   = 2
  message_retention = 7
}

resource "azurerm_eventhub_consumer_group" "processor" {
  name                = "nostradamus"
  namespace_name      = azurerm_eventhub_namespace.events.name
  eventhub_name       = azurerm_eventhub.borrower_events.name
  resource_group_name = azurerm_resource_group.nostradamus.name
}

# Lake storage for the Iceberg tables.
resource "azurerm_storage_account" "lake" {
  name                     = "stnostradamuslake"
  resource_group_name      = azurerm_resource_group.nostradamus.name
  location                 = azurerm_resource_group.nostradamus.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true
}
