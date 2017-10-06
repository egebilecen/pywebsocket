function EB_Websocket(host,port,auto_run){
    if(typeof host === "undefined" || typeof port === "undefined")
        throw new DOMException("Host or port param is undefined.");
    if(typeof auto_run !== "boolean")
        auto_run = false;
    
    var EB_Websocket = {
        socket    : null,
        handlers  : {},
        onOpen    : null,
        onMessage : function(obj){
            try{
                var data = JSON.parse(obj.data);
            }
            catch(err){
                var data = {where:"null",data:{}};
            }
            if(EB_Websocket.handlers.hasOwnProperty(data.where))
                EB_Websocket.handlers[data.where](data.data);
        },
        onClose   : null,
        onError   : null,
        close     : function(){
            EB_Websocket.socket.close();
            EB_Websocket.socket = null;
        },
        setOpenEvent : function(func){
            EB_Websocket.socket.onopen = func;
        },
        setCloseEvent : function(func){
            EB_Websocket.socket.onclose = func;
        },
        setErrorEvent : function(func){
            EB_Websocket.socket.onerror = func;
        },
        on : function(name, func){
            EB_Websocket.handlers[name] = func;
        },
        emit : function(name, data){
            var re_data = JSON.stringify({where:name,data:data});
            EB_Websocket.socket.send(re_data);
        },
        run : function(){
            EB_Websocket.socket = new WebSocket("ws://"+host+":"+port);
            EB_Websocket.socket.onmessage = EB_Websocket.onMessage;
        }
    }
    if(auto_run) EB_Websocket.run();
    return EB_Websocket;
}