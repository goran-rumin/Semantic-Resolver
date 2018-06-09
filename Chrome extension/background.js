console.log("Background page starting")
current_executions = []
processed_data = {}
chrome.storage.local.get("processed_data", function(saved_data){
	if(saved_data.processed_data == undefined){
		return
	}
	processed_data = saved_data.processed_data
})
chrome.runtime.onMessage.addListener(
	function(request, sender, sendResponse) {
		if(request.text.length == 0){
			return;
		}
		if($.inArray(sender.tab.url, current_executions) != -1){
			showNotification(sender.tab.url + " is already being processed")
			return;
		}
		if(sender.tab.url in processed_data){
			if(processed_data[sender.tab.url].length==0){
				showNotification("You already reviewed current article")
			}
			else{
				showNotification("Current article is available for review")
			}
			return;
		}
		request.link = sender.tab.url
		current_executions.push(sender.tab.url)
		$.ajax("http://localhost:8080/relations/find", {
			method: "POST",
			data: JSON.stringify(request), 
			success: function(data){
				console.log(JSON.stringify(data))
				chrome.tabs.sendMessage(sender.tab.id, {status: "processed"}, function(response) {});
				showNotification('Text processing finished: ' + data.relations.length + ' relations found')
				current_executions.splice(current_executions.indexOf(sender.tab.url), 1)
				processed_data[sender.tab.url] = data.relations
				saveData(processed_data)
			},
			error: function(error){
				current_executions.splice(current_executions.indexOf(sender.tab.url), 1)
				console.log(JSON.stringify(error))
				showNotification('Text processing error')
			},
			headers: {"Content-Type": "application/json"}
		})
      sendResponse({status: "submited"});
	  showNotification('Text processing started')
	}
);

function showNotification(message){
	chrome.notifications.create({type: "basic", iconUrl: "icon.png", title: 'SemanticResolver', message: message})
}

function getRelations(){
	return processed_data
}

function removeRelation(article, relation){
	processed_data[article].splice(processed_data[article].indexOf(relation), 1)
	saveData(processed_data)
}

function removeRelations(article){
	processed_data[article] = []
	saveData(processed_data)
}

function saveData(value){
	chrome.storage.local.set({"processed_data": value})
}

chrome.runtime.onInstalled.addListener(function() {
  chrome.declarativeContent.onPageChanged.removeRules(undefined, function() {
    chrome.declarativeContent.onPageChanged.addRules([
      {
        conditions: [
          new chrome.declarativeContent.PageStateMatcher({
            pageUrl: { urlContains: 'edition.cnn.com' },
          }),
		  new chrome.declarativeContent.PageStateMatcher({
            pageUrl: { urlContains: 'bbc.com' },
          }),
		  new chrome.declarativeContent.PageStateMatcher({
            pageUrl: { urlContains: 'huffingtonpost.com' },
          }),
		  new chrome.declarativeContent.PageStateMatcher({
            pageUrl: { urlContains: 'nytimes.com' },
          }),
		  new chrome.declarativeContent.PageStateMatcher({
            pageUrl: { urlContains: 'theguardian.com' },
          })
        ],
        actions: [ new chrome.declarativeContent.ShowPageAction() ]
      }
    ]);
  });
});