$(document).ready(function(){
	text_elements = $(".story-body-text")
	text = ""
	for(i=0; i<text_elements.length; i++){
		text_element = text_elements[i].innerText.trim()
		if(contains_sentence(text_element)){
			text += text_element + " "
		}
	}
	text = text.replace(/^.*? — /, "")
	chrome.runtime.sendMessage({"text": text}, function(response) {
		if(response.status == "submited"){
		}
	});
})

function contains_sentence(text){
	return text.trim().endsWith('.') || text.trim().endsWith('.”') || text.trim().endsWith('.)')
}

chrome.runtime.onMessage.addListener(
	function(request, sender, sendResponse) {
		if(request.status == "processed"){
		}
	}
);