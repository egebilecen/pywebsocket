function EB_Websocket(host,port,auto_run){
    if(typeof host === "undefined" || typeof port === "undefined")
        throw new DOMException("Host or port param is undefined.");
    if(typeof auto_run !== "boolean")
        auto_run = false;

    var EB_Websocket = {
        socket      : null,
        handlers    : {},
        storedEmits : [],
        onOpen    : null,
        onMessage : function(obj){
            var data;
            try{
                data = JSON.parse(obj.data);
            }
            catch(err){
                data = {where:"null",data:{}};
            }
            if(EB_Websocket.handlers.hasOwnProperty(data.where))
                EB_Websocket.handlers[data.where](data.data);
            else
                console.error("Couldn't find handler for \""+data.where+"\".");
        },
        onClose   : null,
        onError   : null,
        close     : function(){
            EB_Websocket.socket.close();
            EB_Websocket.socket = null;
        },
        setErrorEvent : function(func){
            EB_Websocket.socket.onerror = func;
        },
        setDisconnectEvent : function(func){
            EB_Websocket.socket.onclose = function(){
                if(EB_Websocket.status === 1)
                    func();
            };
        },
        on : function(name, func){
            EB_Websocket.handlers[name] = func;
        },
        emit : function(name, data){
            try {
                var re_data = JSON.stringify({where: name, data: data});
                EB_Websocket.socket.send(re_data);
            }
            catch(err){
                EB_Websocket.storedEmits.push({name:name, data:data})
            }
        },
        run : function(){
            EB_Websocket.socket = new WebSocket("ws://"+host+":"+port);
            EB_Websocket.socket.onopen    = function(){
                if( EB_Websocket.storedEmits.length > 0 )
                {
                    for( var i=0; i < EB_Websocket.storedEmits.length; i++ )
                    {
                        var emitObj = EB_Websocket.storedEmits[i];
                        EB_Websocket.emit(emitObj.name, emitObj.data);
                    }
                }
                EB_Websocket.status = 1;
            };
            EB_Websocket.socket.onmessage = EB_Websocket.onMessage;
        },
        status : 0
    };
    if(auto_run) EB_Websocket.run();
    return EB_Websocket;
}
