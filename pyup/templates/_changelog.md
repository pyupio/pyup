{% for version, log in changelog.items() %}
>### {{ version }}
{% for line in log.splitlines() %}
{% if line %}>{{ line }}{% endif %}{% endfor %}

{% endfor %}
