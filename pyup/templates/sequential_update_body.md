{% if requirement.is_pinned %}
There's a new version of [{{ requirement.full_name }}](https://pypi.python.org/pypi/{{ requirement.name }}) available.
You are currently using **{{ requirement.version }}**. I have updated it to **{{ requirement.latest_version_within_specs }}**

{% else %}
{{ requirement.full_name }} is not pinned to a specific version.

I'm pinning it to the latest version **{{ requirement.latest_version_within_specs }}** for now.
{% endif %}

{% if requirement.changelog %}
{% with changelog=requirement.changelog %}
### Changelog
> {% include "_changelog.md" %}
{% endwith %}
{% elif api_key %}
*I couldn't find a changelog for this release. Do you know where I can find one? [Tell me!](https://github.com/pyupio/changelogs/issues/new)*
{% endif %}

Happy merging! 🤖
{% include "_api_key.md" %}
