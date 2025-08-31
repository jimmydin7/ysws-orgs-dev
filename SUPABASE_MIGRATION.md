# Supabase Migration Guide

## Overview

This document outlines the steps taken to migrate the application from using JSON files for data storage to using Supabase, a PostgreSQL-based backend-as-a-service platform.

## Changes Made

1. Added Supabase dependencies to `requirements.txt`
2. Created a `.env.template` file for Supabase credentials
3. Created a `db.py` module to handle Supabase database operations
4. Created a SQL schema file (`supabase_schema.sql`) for setting up Supabase tables
5. Updated the application code to use Supabase instead of JSON files

## Setup Instructions

### 1. Set Up Supabase

1. Create a Supabase account at [https://supabase.com](https://supabase.com)
2. Create a new project
3. Get your Supabase URL and API keys from the project settings

### 2. Configure Environment Variables

1. Copy the `.env.template` file to `.env`:
   ```
   cp .env.template .env
   ```

2. Edit the `.env` file and add your Supabase credentials:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_api_key
   SUPABASE_SERVICE_KEY=your_supabase_service_key
   FLASK_SECRET_KEY=your_flask_secret_key
   ```

### 3. Set Up Database Tables

1. In your Supabase project, go to the SQL Editor
2. Copy the contents of `supabase_schema.sql` and run it to create the necessary tables and indexes

### 4. Install Dependencies

```
pip install -r requirements.txt
```

### 5. Run the Application

```
python app.py
```

## Data Migration

The SQL schema includes initial data for the superadmin user and admin key. If you have existing data in your JSON files that you want to migrate, you can use the following steps:

1. Export your JSON data
2. Format it for SQL insertion
3. Run the SQL commands in the Supabase SQL Editor

Alternatively, you can create a migration script to automate this process.

## Database Schema

### Users Table
- `id`: Serial primary key
- `username`: Text, unique, not null
- `superadmin`: Boolean, default false
- `created_at`: Timestamp with time zone, default now()

### Admin Keys Table
- `id`: Serial primary key
- `name`: Text, not null
- `key`: Text, unique, not null
- `generated_by`: Text, not null
- `generated_at`: Text, not null
- `created_at`: Timestamp with time zone, default now()

### Activity Logs Table
- `id`: Serial primary key
- `timestamp`: Timestamp with time zone, default now()
- `username`: Text, not null
- `action`: Text, not null
- `details`: Text
- `created_at`: Timestamp with time zone, default now()

## Troubleshooting

- If you encounter connection issues, verify your Supabase URL and API keys
- Check that your Supabase project is active and accessible
- Ensure that the tables have been created correctly in Supabase