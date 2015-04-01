The Python Shell Plugin is intended for accessing application internals
and debugging plugins.

When the plugin is enabled (File > Preferences > Plugins) activate the shell
by clicking on View > Shell. Each shell as two local variables: `app` represents
the whole application and `instance` represents the current instance.

A short example (retrieving a list of active backend plugins):

```
>>> app.plugins.get_plugins("crunchyfrog.backend")
<<< 
[<class 'cf.backends.sqlite.SQLiteBackend'>,
 <class 'cf.backends.mysql.MySQLBackend'>,
 <class 'cf.backends.ldapbe.LDAPBackend'>,
 <class 'cf.backends.oracle.OracleBackend'>,
 <class 'cf.backends.postgres.PostgresBackend'>]
>>> 
```

Read the [API documentation](http://cf.andialbrecht.de/api) for more information.

There's an example plugin in the `docs` directory.