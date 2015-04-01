# Connecting #

Open the [Datasource Manager](DatasourceManager.md) to create a new LDAP connection.

The following connection parameters are supported:

| **Parameter** | **Comment** |
|:--------------|:------------|
| Host        | defaults to `localhost`|
| Port        | defaults to `389` |
| Base DN     |  |
| User        | leave empty for anonymous bind |
| Password    |  |

When finished, the new connection will be displayed in the navigator. To connect
to this datasource, right click on the entry and click _"Connect"_.


# Browsing #

Once connected to a LDAP datasource use the navigator to browse through the object tree. Right click
on any object within the tree and choose _"Details"_ to see the attributes for
this object in the main view.

![http://cf.andialbrecht.de/static/img/screens/ldap_details_thumb.png](http://cf.andialbrecht.de/static/img/screens/ldap_details_thumb.png)


# Searching #

The backend provides a simple search interface. To open a new search right-click on
any element in the navigator tree and choose _"Find"_ to use this object as
your search base. A search form will be displayed in the main view:

![http://cf.andialbrecht.de/static/img/screens/ldap_search_thumb.png](http://cf.andialbrecht.de/static/img/screens/ldap_search_thumb.png)

| **Search DN** | Base DN for the search |
|:--------------|:-----------------------|
| **Filter** | Filter string (e.g. `(objectclass=inetOrgPerson)`|
| **Attributes** | Comma-separated list of attributes that should be returned |
| **Scope** | Either _one level_ the search only the given search DN or _sub tree_ to search all underlying nodes too|

To export search results right-click on the results list.

# Future Development #

  * LDIF import/export
  * implement async calls
  * SSL connections