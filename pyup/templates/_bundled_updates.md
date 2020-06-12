{% if updates %}
{% for u in updates %}
{% with requirement=u.requirement %}
### Update [{{ requirement.full_name }}](https://pypi.org/project/{{ requirement.name }}) from **{{ requirement.version }}** to **{{ requirement.latest_version_within_specs }}**.
{% if requirement.changelog %}
{% with changelog=requirement.changelog %}{% include "_changelog.md" %} {% endwith %}
{% endif %}
{% endwith %}
{% endfor %}
{% else %}
It looks like you have been working hard to keep all dependencies updated so far.
{% endif %}
