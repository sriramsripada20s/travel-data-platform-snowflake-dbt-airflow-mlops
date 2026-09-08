{# 
  ============================================================================
  MACRO: generate_schema_name
  PURPOSE: Force exact schema names (STAGING, INTERMEDIATE, MARTS).
  ============================================================================
  WHY THIS EXISTS:
  By default, dbt combines your target schema with your custom schema name:
      <target_schema>_<custom_schema_name>  -->  e.g., "DEV_USER_staging"
  
  This macro overrides that built-in behavior:
  1. If a custom schema IS set (e.g., schema: staging), use it exactly.
  2. If NO custom schema is set, fall back to your default target schema.
  ============================================================================
#}

{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}

{%- endmacro %}