function EB_Websocket(host,port, debug){
    if(typeof host === "undefined" || typeof port === "undefined")
        throw new DOMException("Host or port param is undefined.");
    if(typeof debug !== "boolean")
        debug = false;

    var EB_Websocket = {
        socket      : null,
        debug       : debug,
        handlers    : {},
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
                if(EB_Websocket.debug) console.error("Couldn't find handler for \""+data.where+"\".");
        },
        close : function(){
            EB_Websocket.socket.close();
            EB_Websocket.socket = null;
            EB_Websocket.status = 0;
            EB_Websocket.onClose();
        },
        setErrorEvent : function(func){
            EB_Websocket.socket.onerror = function(){
                func();
                EB_Websocket.status = 0;
            };
        },
        setDisconnectEvent : function(func){
            EB_Websocket.socket.onclose = function(){
                if(EB_Websocket.status === 1)
                {
                    func();
                    EB_Websocket.status = 0;
                }
            };
        },
        on : function(name, func){
            EB_Websocket.handlers[name] = func;
        },
        emit : function(name, data){
            var re_data = encodeURIComponent(JSON.stringify({where: name, data: data}));
            EB_Websocket.socket.send(re_data);
        },
        release : function(key){ //release the handler for this key
            if(typeof EB_Websocket.handlers[key] !== "undefined")
            {
                delete EB_Websocket.handlers[key];
                return true;
            }

            return false;
        },
        run : function(){
            EB_Websocket.socket = new WebSocket("ws://"+host+":"+port);
            EB_Websocket.socket.onopen = function(){
                var event = document.createEvent("Event");
                event.initEvent("EB_Websocket_Connection");
                document.dispatchEvent(event);
                EB_Websocket.status = 1;
            };
            EB_Websocket.socket.onmessage = EB_Websocket.onMessage;
        },
        status : 0
    };
    EB_Websocket.run();

    return {
        close : EB_Websocket.close,
        setErrorEvent : EB_Websocket.setErrorEvent,
        setDisconnectEvent : EB_Websocket.setDisconnectEvent,
        on : EB_Websocket.on,
        emit : EB_Websocket.emit,
        release : EB_Websocket.release,
        getStatus : function(){
            return EB_Websocket.status;
        }
    };
}
