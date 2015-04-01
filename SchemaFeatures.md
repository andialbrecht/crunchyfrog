# Schema browsing and editing #

|				 | **PostgreSQL** | **MySQL** | **SQLite** | **Oracle** |
|:----|:---------------|:----------|:-----------|:-----------|
| **Tables**      | B            | B       | B        | B        |
| **Views**		 | B            | B       | B        | B        |
| **Columns**     | B            | B       | -        | B        |
| **Constraints** | B            | -       | -        | B        |
| **Sequences**   | B            | -       | -        | B        |
| **Indexes**     | B            | -       | -        | B        |
| **Functions<sup>1</sup>**| B            | -       | -        | -        |
| **Schemas<sup>2</sup>**  | B            | B       | -        | -        |
| **Packages**    | -            | -       | -        | B        |

<sup>1)</sup> including procedures

<sup>2)</sup> including namespaces

The LDAP backend supports only browsing and a search interface.


**Legend**

  * _B_ = object is displayed in navigator
  * _D_ = object details (read-only)
  * _A_ = object can be modified (alter...)
  * _N_ = objects can be created or dropped
  * _-_ = not available for RDBMS or not supported yet