
class PgSchema(SchemaProvider):

    def __init__(self):
        SchemaProvider.__init__(self)

    def q(self, connection, sql):
        cur = connection.cursor()._cur
        cur.execute(sql)
        return cur.fetchall()

    def fetch_children(self, connection, parent):


        elif isinstance(parent, Table):
            return [ColumnCollection(table=parent),
                    ConstraintCollection(table=parent),
                    IndexCollection(table=parent)]

        elif isinstance(parent, View):
            return [ColumnCollection(table=parent)]

        elif isinstance(parent, ColumnCollection):
            table = parent.get_data("table")
            ret = []
            sql = "select att.attnum, att.attname, dsc.description from pg_attribute att \
            left join pg_description dsc on dsc.objoid = %(tableoid)s and dsc.objsubid = att.attnum \
            where att.attrelid = %(tableoid)s \
            and att.attnum >= 1" % {"tableoid" : table.get_data("oid")}
            for item in self.q(connection, sql):
                ret.append(Column(item[1], item[2], attnum=item[0]))
            return ret

        elif isinstance(parent, ConstraintCollection):
            ret = []
            table = parent.get_data("table")
            sql = "select con.oid, con.conname \
            from pg_constraint con \
            where con.conrelid = %(relid)s" % {"relid" : table.get_data("oid")}
            for item in self.q(connection, sql):
                ret.append(Constraint(item[1], oid=item[0]))
            return ret

        elif isinstance(parent, IndexCollection):
            ret = []
            table = parent.get_data("table")
            sql = "select rel.oid, rel.relname, dsc.description \
            from pg_class rel \
            left join pg_description dsc on dsc.objoid = rel.oid \
            , pg_index ind \
            where ind.indrelid = %(relid)s and ind.indexrelid = rel.oid" % {"relid" : table.get_data("oid")}
            for item in self.q(connection, sql):
                ret.append(Index(item[1], item[2], oid=item[0]))
            return ret

        elif isinstance(parent, PgLanguageCollection):
            sql = "select lan.oid, lan.lanname, dsc.description \
            from pg_language lan \
            left join pg_description dsc on dsc.objoid = lan.oid"
            return [PgLanguage(item[1], item[2], oid=item[0]) for item in self.q(connection, sql)]

    def get_details(self, connection, obj):
        func = getattr(self, "details_%s" % obj.__class__.__name__.lower(), None)
        if func:
            return func(connection, obj)
        return None

    def details_view(self, connection, view):
        ret = dict()
        sql = "select pg_get_viewdef(%(oid)s, true)" %{"oid" : view.get_data("oid")}
        res = self.q(connection, sql)
        ret[_(u"Definition")] =  res[0][0]
        return ret


try:
    import psycopg2
    import psycopg2.extensions
except ImportError:
    PostgresBackend.INIT_ERROR = _(u"Python module psycopg2 required.")
