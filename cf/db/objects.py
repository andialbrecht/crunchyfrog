# -*- coding: utf-8 -*-

"""Database objects."""

import os
import re

import gtk
import gobject

_ = lambda x: x


class PropertyAttribute(object):
    """Connects a instance attribute to a property."""

    def __init__(self, prop):
        self._prop = prop

    def __get__(self, instance, owner):
        return instance.get_property(self._prop.name)

    def __set__(self, instance, value):
        instance.set_property(self._prop.name, value)


class DBObjectMeta(gobject.GObjectMeta):

    def __new__(cls, name, bases, dct):
        gproperties = dct.get('__gproperties__', {})
        new_cls = gobject.GObjectMeta.__new__(cls, name, bases, dct)
        # Shift up properties one level
        for prop in new_cls.props:
            if getattr(new_cls, prop.name, None) is not None:
                raise ValueError, 'Invalid property name %s' % prop.name
            setattr(new_cls, prop.name, PropertyAttribute(prop))
        return new_cls



class GObjectBase(gobject.GObject):
    """Base class for all object classes in this module.

    This class provides basic functionality like setting properties and
    creating class attributes from them.
    """

    __gproperties__ = dict()
    __metaclass__ = DBObjectMeta


    def __init__(self, initial_data=None):
        """Inititalize the object.

        If *initial_data* is given, :meth:`apply_data` is called to set
        initial data on instance creation time.
        """
        self.__gobject_init__()
        self._data = {}
        self._set_properties_defaults()
        if initial_data is not None:
            self.apply_data(initial_data)

    def _set_properties_defaults(self):
        """Set default value as given in __gproperties___."""
        [self._data.update({p.name: p.default_value})
         for p in gobject.list_properties(self)]
        [self.set_property(p.name, p.default_value)
         for p in gobject.list_properties(self)]

    def do_get_property(self, property):
        """Property getter.

        Returns:
          The properties values.

        Raises:
          AttributeError if the property doesn't exist.
        """
        if property.name in self._data:
            return self._data[property.name]
        else:
            raise AttributeError, 'unknown property %s' % property.name

    def do_set_property(self, property, value):
        """Property setter.

        Raises:
          AttributeError when a property doesn't exist.
        """
        if self._data.has_key(property.name):
            self._data[property.name] = value
        else:
            raise AttributeError, 'unknown property %s' % property.name

    def apply_data(self, data):
        """Applies data to the object.

        If a key is definied in ``__gproperties__`` the value will be set
        as a property. Otherwise it will be set using the :meth:`set_data`
        method.

        *data* is a dictionary mapping attributes and values.
        """
        for key, value in data.iteritems():
            if key in self._data:
                self.set_property(key, value)
            else:
                self.set_data(key, value)
                setattr(self, key, value)



class DBObject(GObjectBase):

    __gproperties__ = {
        'name' : (
            gobject.TYPE_STRING,
            'Name', 'Object name',
            '',
            gobject.PARAM_READWRITE),
        'comment' : (
            gobject.TYPE_STRING,
            'Comment', 'Object comment',
            '',
            gobject.PARAM_READWRITE),
        'refresh_required' : (
            gobject.TYPE_BOOLEAN,
            'Refresh required', 'Refresh required',
            True,
            gobject.PARAM_READWRITE),
        }

    typeid = ''
    typestr = u'???'
    icon = 'gtk-missing-image'

    def __init__(self, meta, **kwds):
        GObjectBase.__init__(self, initial_data=kwds)
        self.meta = meta

    def __repr__(self):
        return '<%s "%s" at 0x%07x>' % (self.__class__.__name__,
                                        self.get_display_name(), id(self))

    def get_display_name(self):
        return self.name

    def get_full_name(self):
        return self.name

    def refresh(self):
        self.meta.engine.refresh(self)

    def property_matches(self, name, value):
        if '__' in name:
            name, options = name.split('__', 1)
            if options == 'ilike':
                p = re.compile(value, re.IGNORECASE)
                cmp_func = lambda x, y: bool(p.match(x))
        else:
            cmp_func = lambda x, y: x == y
        if name in self._data:
            cmp_value = self.get_property(name)
        else:
            cmp_value = self.get_data(name)
        return cmp_func(value, cmp_value)

    def get_children(self):
        return self.meta.get_children(self)

    def get_icon_pixbuf(self):
        """Returns a pixbuf for this object of 16x16 size."""
        if self.icon.startswith('gdbo-'):
            dir_name = os.path.join(os.path.dirname(__file__),
                                    'pixmaps')
            fname = os.path.join(dir_name, '%s.png' % self.icon)
            return gtk.gdk.pixbuf_new_from_file(fname)
        else:
            it = gtk.icon_theme_get_default()
            return it.load_icon(self.icon, gtk.ICON_SIZE_MENU,
                                gtk.ICON_LOOKUP_GENERIC_FALLBACK)


class Collection(DBObject):
    """Base class for collections.

    Signals:
      :collection-refreshed: Emited when a collections was refreshed.
        `def callback(collection)`

    @cvar objects: List of objects in this collection.
    @type objects: C{list}
    @cvar typeid: Type identifier
    @type typeid: C{str}
    @cvar typestr: Human-readable representation of C{typeid}
    @type typestr: C{str}
    @cvar objklass: The object class provided by this collection.
    @type objklass: L{DBObject}
    @ivar provider: The current provider.
    @type provider: L{SchemaProvider}
    @ivar backend: The current engine.
    @type backend: L{engines.NullEngine}
    """

    __gproperties__ = {"count" : (gobject.TYPE_LONG,
                                  "Count", "Number of objects as seen in database",
                                  0, long(99999999), 0,
                                  gobject.PARAM_READWRITE),
                       "objects" : (gobject.TYPE_PYOBJECT,
                                    "Objects", "Objects",
                                    gobject.PARAM_READWRITE),
                       }
    __gsignals__ = {"collection-refreshed" : (gobject.SIGNAL_RUN_LAST,
                                         gobject.TYPE_NONE,
                                         tuple())}

    icon = 'gtk-open'

    def __init__(self, meta, items_class, **kwds):
        DBObject.__init__(self, meta, **kwds)
        self.objects = []
        self.meta = meta
        self.items_class = items_class
#        self.provider.connect("backend-changed", self.on_backend_changed)

#    def on_backend_changed(self, provider, backend):
#        """Callback for L{SchemaProvider} C{backend-changed}."""
#        if self.provider == provider and backend != self.backend:
#            self.backend = backend

    def get_display_name(self):
        return self.typestr

#    def check_refresh(self):
#        """
#        Deprecated (see L{filter}).
#        @warning: Deprecated.
#        """
#        deprecated()
#        if self.refresh_required: self.refresh_objects()

    def find(self, *kwds):
        if self.props.refresh_required:
            self.meta.engine.refresh(self)
        res = self.meta.find(cls=self.items_class, parent=self)
        return res

    # FIXME(andi): Replace this with normal list behavior.
    def exists(self, obj):
        """Returns C{True} if C{obj} exists in this collection.

        @param obj: An object
        @type obj: L{DBObject}
        @return: C{True}/C{False}
        @rtype: C{bool}
        """
        return obj in self.objects

    def refresh(self):
        """
        Deprecated (see L{filter}).
        @warning: Deprecated: Use L{filter} instead.
        @todo 0.1.5: Remove this method.
        """
        deprecated("Use filter() instead.")
        self.provider.log("%r.refresh() called")
        self.add_task(self.refresh_count)
        self.add_task(self.refresh_objects)

    def refresh_count(self):
        """
        Deprecated (see L{filter}).
        @warning: Deprecated. Use L{filter} instead.
        @todo 0.1.5: Remove this method.
        """
        deprecated("Use filter() instead.")
        if self.backend:
            self.count = self.backend.get_object_count(self.objklass)
        else:
            self.count = 0

    def refresh_objects(self):
        """
        Deprecated (see L{filter}).
        @warning: Deprecated. Use L{filter} instead.
        @todo 0.1.5: Remove this method.
        """
        deprecated("Use filter() instead.")
        self.objects = []
        if self.backend:
            [self.objects.append(s) for s in self.backend.get_objects(self.objklass)]
        self.refresh_required = False
        self.emit("collection-refreshed")

    def refresh_needed(self):
        """
        Deprecated (see L{filter}).
        @warning: Deprecated. Use L{filter} instead.
        @todo 0.1.5: Remove this method.
        """
        deprecated("Use filter() instead.")
        self.refresh_count()
        return len(self.objects or []) <> self.count

    def all(self):
        """
        Deprecated (see L{filter}).
        @warning: Deprecated. Use L{filter} instead.
        @todo 0.1.5: Remove this method.
        """
        deprecated("Use filter() instead.")
        self.check_refresh()
        return self.objects

    def apply_filter(self, items, *args, **kwargs):
        """Filtering process.

        This method applies the given filter keywords to a list
        of objects and returns a filtered list.

        @param items: List of objects
        @type items: C{list}
        @return: Filtered list of objects
        @rtype: C{list}
        """
        def filters_match(obj, *args, **kwargs):
            for key in kwargs.keys():
                st = kwargs.get(key)
                if hasattr(obj, key):
                    cmp_item = getattr(obj, key)
                else:
                    cmp_item = obj.get_data(key)
                if not cmp_item:
                    return False
                if type(st) in [unicode, str]:
                    try:
                        p = re.compile(st)
                        if type(cmp_item) in [unicode, str]:
                            if not p.search(cmp_item):
                                return False
                        elif hasattr(cmp_item, "name"):
                            if not p.search(getattr(cmp_item, "name")):
                                return False
                        else:
                            return False
                    except:
                        return False
                else:
                    if not cmp_item == st:
                        return False
            return True

        ret = []
        for item in items or []:
            if filters_match(item, **kwargs):
                ret.append(item)
        return list(set(ret))

    ## def filter(self, *args, **kwargs):
    ##     """
    ##     Returns a filtered list of objects.

    ##     If this method is called without any keywords, the
    ##     complete list of objects will be returned.

    ##     All keywords, except the special ones mentioned below, are used
    ##     to filter the results. For example, C{filter(name="foo")} would
    ##     return all items in the collection with "Foo" as their object name.

    ##     The keywords are passed to the engines C{filter} method, which does
    ##     the real filtering and schema queries. But only if the C{_cached}
    ##     keyword is C{False}.

    ##     Objects returned by the engine are filtered (again) by L{apply_filter}.
    ##     Finally the objects are sorted within this method.

    ##     If the C{_create} keyword is present and C{True}, an object
    ##     based on L{objklass} is created with the given keywords, if the filtering
    ##     process returns no results.

    ##     @keyword _create: Create object if it doesn't exist and return it (default: C{False}).
    ##     @type _create: C{bool}
    ##     @keyword _cached: Don't query the database, return objects from internal cache (default: C{False}).
    ##     @type _cached: C{bool}
    ##     @return: Filtered list of objects.
    ##     @rtype: C{list}
    ##     """
    ##     if kwargs.has_key("_create"):
    ##         create_object = kwargs.get("_create")
    ##         del kwargs["_create"]
    ##     else:
    ##         create_object = False
    ##     if kwargs.has_key("_cached"):
    ##         cached = kwargs.get("_cached")
    ##         del kwargs["_cached"]
    ##     else:
    ##         cached = False
    ##     if cached:
    ##         items = self.objects
    ##     else:
    ##         items = self.backend.filter(self, *args, **kwargs)
    ##     ret = self.apply_filter(items,
    ##                             *args, **kwargs)
    ##     if not ret and create_object:
    ##         obj = self.objklass(self.provider, initial_data = kwargs)
    ##         self.objects.append(obj)
    ##         ret = [obj]
    ##     self.provider.cache.append(ret)
    ##     ret.sort()
    ##     return ret



class Argument(DBObject):

    __gproperties__ = {"type" : (gobject.TYPE_PYOBJECT,
                                    "Type", "Argument data type",
                                    gobject.PARAM_READWRITE),
                       "mode" : (gobject.TYPE_STRING,
                                        "In-Out-InOut", "In-Out-InOut",
                                        "",
                                        gobject.PARAM_READWRITE),
                       "name" : (gobject.TYPE_STRING,
                                        "Name", "Name",
                                        "",
                                        gobject.PARAM_READWRITE),
                       "sortorder" : (gobject.TYPE_INT,
                                        "Sort order", "Sort order",
                                        -1, 10000, -1,
                                        gobject.PARAM_READWRITE),
                       "parent" : (gobject.TYPE_PYOBJECT,
                                        "Parent object", "Parent object",
                                        gobject.PARAM_READWRITE)}

    def __init__(self, provider, *args, **kwargs):
        DBObject.__init__(self, provider, *args, **kwargs)
        self.typeid = "argument"
        self.typestr = _(u"Arguments")


class Arguments(Collection):

    def __init__(self, provider, parent):
        #self.backend = provider.engine
        self.typeid = "arguments"
        self.typestr = _(u"Arguments")
        self.parent = parent
        Collection.__init__(self, provider, self.backend, Argument)

class Cache(Collection):

    def __init__(self, provider):
        self.typeid = "dbschema_cache"
        self.typestr = _(u"dbschema_cache")
        self.backend = None
        Collection.__init__(self, provider, self.backend, None)

    def append(self, items):
        self.objects += items
        self.objects = list(set(self.objects))

class Columns(Collection):

    def __init__(self, meta, **kwds):
        Collection.__init__(self, meta, Column, **kwds)
        self.typeid = "columns"
        self.typestr = _(u"Columns")

    def new(self):
        col = Column(self.meta, self.parent)
        self.objects.append(col)
        return col

class Column(DBObject):

    __gproperties__ = {"sortorder" : (gobject.TYPE_INT,
                                      "Sort order", "Sort order", -1, 10000, -1,
                                      gobject.PARAM_READWRITE),
                       "type" : (gobject.TYPE_PYOBJECT,
                                 "Data type", "Data type",
                                 gobject.PARAM_READWRITE),
                       "default" : (gobject.TYPE_PYOBJECT,
                                    "Default", "Default value",
                                    gobject.PARAM_READWRITE),
                       "pk" : (gobject.TYPE_BOOLEAN,
                               "Primary key", "Primary key", False,
                               gobject.PARAM_READWRITE),
                       "nullable" : (gobject.TYPE_BOOLEAN,
                                     "Nullable", "Nullable", False,
                                     gobject.PARAM_READWRITE),
                       "parent" : (gobject.TYPE_PYOBJECT,
                                   "Parent", "Parent object",
                                   gobject.PARAM_READWRITE)}

    icon = 'gdbo-column'

    def __init__(self, meta, parent, *args, **kwargs):
        kwargs["parent"] = parent
        DBObject.__init__(self, meta, *args, **kwargs)
        self.typeid = "column"
        self.typestr = _(u"Column")

    def __cmp__(self, other):
        return cmp(self.sortorder, other.sortorder)

class Constraints(Collection):

    def __init__(self, meta, **kwds):
        Collection.__init__(self, meta, Constraint, **kwds)
        self.typeid = "constraints"
        self.typestr = _(u"Constraints")

    def new(self):
        c = Constraint(self.provider, self.parent)
        self.objects.append(c)
        return c

class Constraint(DBObject):

    __gproperties__ = {"type" : (gobject.TYPE_STRING,
                                 "Sort order", "Sort order", None,
                                 gobject.PARAM_READWRITE),
                       "check_expression" : (gobject.TYPE_STRING,
                                             "Check expression", "Check expression", "",
                                             gobject.PARAM_READWRITE),
                       "columns" : (gobject.TYPE_PYOBJECT,
                                    "Primary/unique columns", "Primary key/unique columns",
                                    gobject.PARAM_READWRITE),
                       "fkcolumns" : (gobject.TYPE_PYOBJECT,
                                      "Foreign key columns", "Foreign key columns",
                                      gobject.PARAM_READWRITE),
                       "parent" : (gobject.TYPE_PYOBJECT,
                                   "Parent object", "Parent object",
                                   gobject.PARAM_READWRITE)}

    icon = 'gtk-spell-check'

    def __init__(self, meta, parent, *args, **kwargs):
        kwargs["parent"] = parent
        DBObject.__init__(self, meta, *args, **kwargs)
        self.typeid = "constraint"
        self.typestr = _(u"Constraint")
        self.columns = Columns(self.meta, parent=self)
        self.meta.set_object(self.columns)
        self.fkcolumns = Columns(self.meta, parent=self)

class Function(DBObject):

    __gproperties__ = {"arguments" : (gobject.TYPE_PYOBJECT,
                                    "Arguments", "Argument list",
                                    gobject.PARAM_READWRITE)}

    icon = 'gdbo-function'

    def __init__(self, provider, *args, **kwargs):
        DBObject.__init__(self, provider, *args, **kwargs)
        self.typeid = "function"
        self.typestr = _(u"Function")
        self.arguments = Arguments(self.provider, self)


class Functions(Collection):

    def __init__(self, provider):
        self.backend = None
        self.typeid = "functions"
        self.typestr = _(u"Functions")
        Collection.__init__(self, provider, self.backend, Function)


class Table(DBObject):

    __gproperties__ = {"columns" : (gobject.TYPE_PYOBJECT,
                                    "Columns", "Column list",
                                    gobject.PARAM_READWRITE),
                       "constraints" : (gobject.TYPE_PYOBJECT,
                                        "Constraints", "Table constraints",
                                        gobject.PARAM_READWRITE)}

    icon = 'gdbo-table'

    def __init__(self, meta, **kwds):
        DBObject.__init__(self, meta, **kwds)
        self.typeid = "table"
        self.typestr = _(u"Table")
        self.columns = Columns(self.meta, parent=self)
        self.meta.set_object(self.columns)
        self.constraints = Constraints(self.meta, parent=self)
        self.meta.set_object(self.constraints)

    def get_full_name(self):
        if hasattr(self, "schema") and not self.schema.is_default:
            n = "%s.%s" % (self.schema.name, self.name)
        else:
            n = self.name
        return n

    def get_insert_sql(self, col_values = dict()):
        sql = "insert into %s" % self.name
        cols = list()
        vals = list()
        my_columns = list()
        [my_columns.append(x.name) for x in self.columns.filter()]
        for key in col_values.keys():
            if not key in my_columns: continue
            cols.append(key)
            vals.append("%r" % col_values[key])
        sql += " (%s) values" % ", ".join(cols)
        sql += " (%s)" % ", ".join(vals)
        return sql

    def get_row_count(self):
        sql = "select count(*) from %s" % self.get_full_name()
        return self.provider.engine.run_query(sql, True)[0]

    def insert(self, *args, **kwargs):
        sql = self.get_insert_sql(kwargs)
        e = self.provider.engine
        e.begin_modification()
        e.modifications.append(sql)
        ret_code, err_msg = e.end_modification(True)
        return ret_code, err_msg




class Tables(Collection):

    def __init__(self, meta, **kwds):
        Collection.__init__(self, meta, Table, **kwds)
        self.typeid = "tables"
        self.typestr = _(u"Tables")


class Schema(DBObject):

    __gproperties__ = {"is_default" : (gobject.TYPE_BOOLEAN,
                                  "Name", "Object name",
                                  False,
                                  gobject.PARAM_READWRITE)}

    def __init__(self, meta, **kwds):
        DBObject.__init__(self, meta, **kwds)
        self.typeid = "schema"
        self.typestr = _(u"Schema")


class Schemata(Collection):

    def __init__(self, meta):
        Collection.__init__(self, meta, Schema)
        self.typeid = "schemata"
        self.typestr = _(u"Schemata")
#        self.functions = Functions(provider)
#        self.tables = Tables(provider)
#        self.views = Views(provider)

class Sequence(DBObject):

    # Numbers can *very* large, store them as strings...
    __gproperties__ = {"minValue" : (gobject.TYPE_STRING,
                                  "Min. value", "Min. value",
                                  "",
                                  gobject.PARAM_READWRITE),
                       "maxValue" : (gobject.TYPE_STRING,
                                  "Max. value", "Max. value",
                                  "",
                                  gobject.PARAM_READWRITE),
                       "lastValue" : (gobject.TYPE_STRING,
                                  "Last value", "Last value",
                                  "",
                                  gobject.PARAM_READWRITE),
                       "incrementBy" : (gobject.TYPE_STRING,
                                  "Increment by", "Increment by",
                                  "",
                                  gobject.PARAM_READWRITE),}

    icon = 'gtk-sort-ascending'

    def __init__(self, provider, *args, **kwargs):
        DBObject.__init__(self, provider, *args, **kwargs)
        self.typeid = "sequence"
        self.typestr = _(u"Sequence")


class Sequences(Collection):

    def __init__(self, provider):
        self.backend = None
        self.typeid = "sequences"
        self.typestr = _(u"Sequences")
        Collection.__init__(self, provider, self.backend, Sequence)

class User(DBObject):

    __gproperties__ = {"isCurrent" : (gobject.TYPE_BOOLEAN,
                                  "Current user", "Current user",
                                  False,
                                  gobject.PARAM_READWRITE)}

    icon = 'gdbo-user'

    def __init__(self, meta, **kwds):
        DBObject.__init__(self, meta, **kwds)
        self.typeid = "user"
        self.typestr = _(u"User")
        self.has_comment = False


class Users(Collection):

    def __init__(self, meta):
        Collection.__init__(self, meta, User)
        self.typeid = "users"
        self.typestr = _(u"Users")

class Trigger(DBObject):

    __gproperties__ = {"table" : (gobject.TYPE_PYOBJECT,
                                    "Table", "Table",
                                    gobject.PARAM_READWRITE),
                       "schema" : (gobject.TYPE_PYOBJECT,
                                    "Schema", "Table's schema",
                                    gobject.PARAM_READWRITE),
                       "source" : (gobject.TYPE_STRING,
                                    "Source", "Source",
                                    None,
                                    gobject.PARAM_READWRITE),}

    def __init__(self, provider, *args, **kwargs):
        DBObject.__init__(self, provider, *args, **kwargs)
        self.typeid = "trigger"
        self.typestr = _(u"Trigger")
        self.connect("notify::table", self.on_notify)

    def on_notify(self, *args):
        self.schema = self.table.schema


class TriggerCollection(Collection):

    def __init__(self, provider):
        self.typeid = "triggercollection"
        self.typestr = _(u"Trigger")
        self.backend = None
        Collection.__init__(self, provider, self.backend, Trigger)


class Type(DBObject):

    __gproperties__ = {"variableLength" : (gobject.TYPE_BOOLEAN,
                                    "Variable length", "Variable length",
                                    False,
                                    gobject.PARAM_READWRITE),
                       "isComposite" : (gobject.TYPE_BOOLEAN,
                                        "Composite type", "Composite type",
                                        False,
                                        gobject.PARAM_READWRITE)}

    def __init__(self, provider, *args, **kwargs):
        DBObject.__init__(self, provider, *args, **kwargs)
        self.typeid = "type"
        self.typestr = _(u"Type")


class Types(Collection):

    def __init__(self, provider):
        self.backend = None
        self.typeid = "types"
        self.typestr = _(u"Types")
        Collection.__init__(self, provider, self.backend, Type)

class Views(Collection):

    def __init__(self, meta, **kwds):
        Collection.__init__(self, meta, View, **kwds)
        self.typeid = "views"
        self.typestr = _(u"Views")
#        self.tables = Tables()

class View(DBObject):

    __gproperties__ = {"columns" : (gobject.TYPE_PYOBJECT,
                                    "Columns", "Column list",
                                    gobject.PARAM_READWRITE),
                       "src" : (gobject.TYPE_STRING,
                                        "View source", "View source",
                                        "",
                                        gobject.PARAM_READWRITE)}

    icon = 'gdbo-table'

    def __init__(self, meta, **kwds):
        DBObject.__init__(self, meta, **kwds)
        self.typeid = "view"
        self.typestr = _(u"View")
        self.columns = Columns(self.meta, parent=self)
        self.meta.set_object(self.columns)

gobject.type_register(Columns)
gobject.type_register(Column)
gobject.type_register(Constraints)
gobject.type_register(Constraint)
gobject.type_register(Functions)
gobject.type_register(Function)
gobject.type_register(Schemata)
gobject.type_register(Schema)
gobject.type_register(Sequences)
gobject.type_register(Sequence)
gobject.type_register(Tables)
gobject.type_register(Table)
gobject.type_register(TriggerCollection)
gobject.type_register(Trigger)
gobject.type_register(Users)
gobject.type_register(User)
gobject.type_register(Views)
gobject.type_register(View)
