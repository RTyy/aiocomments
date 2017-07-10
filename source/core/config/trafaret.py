import trafaret as T


primitive_ip_regexp = r'^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'
dotted_path_regexp = r'^[\.]{0,2}([^\d][\w]+|\.[^\d]\w+)+[^.]$'

TRAFARET = T.Dict({
    T.Key('debug'): T.Bool(),
    T.Key('postgres'):
        T.Dict({
            T.Key('debug'): T.Bool(),
            'database': T.String(),
            'user': T.String(),
            'password': T.String(),
            'host': T.String(),
            'port': T.Int(),
            'minsize': T.Int(),
            'maxsize': T.Int(),
        }),
    T.Key('filestorage'):
        T.Dict({
            T.Key('root'): T.String()
        }),
    T.Key('redis'):
        T.Dict({
            'host': T.String(),
            'port': T.Int(),
        }),
    T.Key('host'): T.String(regex=primitive_ip_regexp),
    T.Key('port'): T.Int(),
    T.Key('apps'): T.List(T.String(regex=r'^[^\d]\w+$')),
    T.Key('middlewares'): T.List(T.String(regex=dotted_path_regexp)),
})
