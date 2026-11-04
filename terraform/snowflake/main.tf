# Snowflake objects the dbt project and Dynamic Tables expect. Design only: never applied.
terraform {
  required_providers {
    snowflake = { source = "Snowflake-Labs/snowflake", version = "~> 1.0" }
  }
}

resource "snowflake_database" "nostradamus" {
  name = "NOSTRADAMUS"
}

resource "snowflake_schema" "bronze" {
  database = snowflake_database.nostradamus.name
  name     = "BRONZE"
}

resource "snowflake_schema" "silver" {
  database = snowflake_database.nostradamus.name
  name     = "SILVER"
}

resource "snowflake_schema" "gold" {
  database = snowflake_database.nostradamus.name
  name     = "GOLD"
}

resource "snowflake_warehouse" "transform" {
  name           = "NOSTRADAMUS_WH"
  warehouse_size = "XSMALL"
  auto_suspend   = 60
}
