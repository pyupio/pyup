<details>
  <summary>Links</summary>
  {% for source, link in package_metadata.items() %}
  {% if link %}
   - {{ source }}: {{ link }}
   {% endif %}
  {% endfor %}
</details>


