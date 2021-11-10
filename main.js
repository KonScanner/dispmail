let file = "./accounts.txt";

function readTextFile(file) {
    var rawFile = new XMLHttpRequest();
    rawFile.open("GET", file, false);
    rawFile.onreadystatechange = function () {
        if (rawFile.readyState === 4) {
            if (rawFile.status === 200 || rawFile.status == 0) {
                var allText = rawFile.responseText;
                var lines = allText.match(/[^\r\n]+/g);
                var usernames = allText.match(/[a-zA-Z.]+[0-9]+@[a-zA-Z]+[.a-zA-Z]+/gm);
                var passwords = allText.match(/:[a-zA-Z0-9!]+./gm);
                // var recoverykeys = allText.match(/:[a-zA-Z0-9]+$/gm);
                var str = '<ul>'
                for (let i = 0; i < usernames.length; i++) {
                    str += '<li>' + usernames[i] + "<br>" + passwords[i].match(/[^:!]+/gm) + "!"
                    '</li>';

                }
                str += '</ul>';
                document.getElementById("accounts").innerHTML = str;
            }
        }
    }
    rawFile.send(null);
};

function searchFunction() {
    readTextFile(file)
    var input, filter, ul, li, a, i, txtValue;
    input = document.getElementById("searchID");
    filter = input.value.toUpperCase();
    ul = document.getElementsByTagName("ul");
    li = ul[0].getElementsByTagName("li");
    for (i = 0; i < li.length; i++) {
        a = li[i];
        txtValue = a.textContent || a.innerText;
        if (txtValue.toUpperCase().indexOf(filter) > -1) {
            li[i].style.display = "";
        } else {
            li[i].style.display = "none";
        }
    }
};