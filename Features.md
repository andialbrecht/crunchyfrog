# Backends #

| **Database**  | **Additional Requirements** | **Remarks** |
|:--------------|:----------------------------|:------------|
| PostgresSQL | python-psycopg2 |  |
| MySQL       | python-mysqldb  |  |
| SQLite3     | python-sqlite3  |  |
| Oracle      | cx\_Oracle       |  |
| [LDAP](LDAPSupport.md) | python-ldap     | experimental |

All backends, except the LDAP backend, support multiple connections.
The PostgreSQL backend supports transactions.

Read SchemaFeatures for details.


# Data Export #

  * CSV
  * OpenDocument spreadsheet


# Plugins #

  * [Python Shell](PythonShell.md)
  * SQL Library
  * Reference Viewer (experimental)