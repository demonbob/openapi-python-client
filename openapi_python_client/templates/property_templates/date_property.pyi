{% macro construct(property, source) %}
{% if property.required %}
{{ property.python_name }} = date.fromisoformat({{ source }})
{% else %}
{{ property.python_name }} = None
if {{ source }} is not None:
    {{ property.python_name }} = date.fromisoformat(cast(str, {{ source }}))
{% endif %}
{% endmacro %}

{% macro transform(property, source, destination) %}
{% if property.required %}
{{ destination }} = {{ source }}.isoformat()
{% else %}
{{ destination }} = {{ source }}.isoformat() if {{ source }} else None
{% endif %}
{% endmacro %}
