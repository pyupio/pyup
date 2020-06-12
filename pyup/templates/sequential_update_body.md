{% if requirement.is_pinned %}
This PR updates [{{ requirement.full_name }}](https://pypi.org/project/{{ requirement.name }}) from **{{ requirement.version }}** to **{{ requirement.latest_version_within_specs }}**.
{% else %}
This PR pins [{{ requirement.full_name }}](https://pypi.org/project/{{ requirement.name }}) to the latest release **{{ requirement.latest_version_within_specs }}**.
{% endif %}

{% if requirement.changelog %}
{% with changelog=requirement.changelog %}
{% include "_changelog.md" %}
{% endwith %}
{% elif api_key %}
*The bot wasn't able to find a changelog for this release. [Got an idea?](https://github.com/pyupio/changelogs/issues/new)*
{% endif %}

{% include "_api_key.md" %}
