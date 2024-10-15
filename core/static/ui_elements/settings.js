/*
    The settings page that pops up when you press the settings icon.
*/

let settingsPage = () => {
    let settingsElement = document.getElementById("settingsPage");
    if(settingsElement.style.display == "block"){
        settingsElement.style.display = "none"
    }else{
        settingsElement.style.display = "block"
    }
}