{#
  ============================================================================
  MACRO: generate_schema_name
  PURPOSE: Controls schema names in Snowflake and creates temporary
           schemas for GitHub Pull Requests.
  ============================================================================
  HOW IT WORKS:
  1. If running a CI test on a GitHub PR:
     Creates a temporary, isolated schema (e.g., RAW_pr_47). This keeps PRs
     from overwriting each other's data. A separate workflow drops this
     schema when the PR closes.
  2. If a model has a custom schema set (e.g., schema: staging):
     Uses that exact custom schema name directly without adding prefixes.
  3. Otherwise:
     Falls back to the target's default schema name.

  NOTE:
  If a model uses a custom schema DURING a PR test, it will build to the
  custom schema instead of a PR-scoped schema (e.g., staging instead of
  staging_pr_47). Since no models currently use custom schemas, this isn't
  an issue right now.
  ============================================================================
#}

{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- if target.name == 'staging' and env_var('DBT_PR_NUMBER', '') != '' -%}
        {{ target.schema }}_pr_{{ env_var('DBT_PR_NUMBER') }}
    {%- elif custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}

{%- endmacro %}
