# Pretty print SQL statements
# by Peter Bengtsson, www.peterbe.com
# August, 2004

# Some modifications by Andi Albrecht, March 2008

import re

__version__='0.1'

def printsql(sql):
    """ simple version of pprint for SQL strings """
    keywords = ('select','from','where','order by','desc','asc',
                'limit','offset','update','delete','insert','set',
                'having','group by','count','table','create',
                'drop','and','or','in','ilike','like',
                'inner join', 'outer join', 'left outer join',
                'join'
                )
    aloner = lambda x: '(\s%s\s|^%s\s|\s%s$)'%(x,x,x)

    re_flags = re.I|re.MULTILINE
    regex = '|'.join(map(aloner, keywords))
    anykeyword = re.compile(regex, re_flags)
    for each in anykeyword.findall(sql):
        each = list(each)
        while '' in each:each.remove('')
        for subeach in each:
            sql = sql.replace(subeach, subeach.upper())

    if len(sql) > 10:

        spad = '  '

        regex = re.compile('(SELECT\s(.*?))(\sFROM\s(.*?)\s)', re_flags)
        found = regex.findall(sql)
        if found:
            sql = sql.replace(found[0][0], 'SELECT\n%s%s\n'%(spad, found[0][1]))
            sql = sql.replace(found[0][2], 'FROM\n %s\n'%found[0][3])

        regex = re.compile('(ORDER BY\s(.*?))(\sLIMIT\s(.*?)\s)', re_flags)
        found = regex.findall(sql)
        if found:
            sql = sql.replace(found[0][0], '\nORDER BY %s\n'%found[0][1])
            sql = sql.replace(found[0][2], 'LIMIT %s\n'%found[0][3])

        regex = re.compile('(\s+WHERE\s(.*?)\s(GROUP BY|ORDER BY|LIMIT))', re_flags)
        found = regex.findall(sql)
        if found:
            sql = sql.replace(found[0][0],
                              '\nWHERE\n%s%s\n%s'%(spad, found[0][1],found[0][2]))

    return sql


def test(s):
    print printsql(s)
    print

if __name__=='__main__':
    print "TESTING SOME SQL"
    print 
    test('select * from foo order by bar;')
    test('''select id, bull, time from foobartable
    where time=1 and shit='yes' order by bar limit 30 offset 10;''')
