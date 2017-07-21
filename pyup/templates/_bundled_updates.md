{% if updates %}
## Updates
Here's a list of all the updates bundled in this pull request.
<table align="center">
{% for u in updates %}
<tr>
<td><b>{{u.requirement.full_name}}</b></td>
<td align="center">{{u.requirement.version}}</td>
<td align="center">&raquo;</td>
<td align="center">{{u.requirement.latest_version_within_specs}}</td>
{% endfor %}
</tr>
</table>
{% else %}
It looks like you have been working hard to keep all dependencies updated so far.
{% endif %}

{% if changelogs %}
## Changelogs
{% for requirement in changelogs %}
{% with changelog=requirement.changelog %}
### {{ requirement.full_name }} {% if requirement.is_pinned %}{{ requirement.version }}{% endif %} -> {{requirement.latest_version_within_specs}}
{% include "_changelog.md" %}
{% endwith %}
{% endfor %}
{% endif %}
