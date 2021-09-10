function $_(selector)
{
    return document.querySelector(selector);
}

function $_a(selector)
{
    return document.querySelectorAll(selector);
}

function str_to_element(text)
{
    var div = document.createElement("div");
    div.innerHTML = text;
    return div.firstChild;
}
