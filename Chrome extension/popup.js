relation_sentence_map = {
	"parentOrganization": "Organization %1 is part of organization %2.",
	"employee": "%2 works for %1.",
	"brand": "Organization %1 owns brand %2.",
	"subOrganization": "Organization %2 is part of organization %1.",
	"spouse": "%1 is married to %2.",
	"relatedTo": "%1 is related to %2.",
	"homeLocation": "%1 lives at %2.",
	"colleague": "%1 knows or works with %2.",
	"children": "%2 is a child of %1.",
	"parent": "%1 is parent of %2.",
	"location": "Organization %1 is located at %2.",
	"containedInPlace": "Location %1 is located within %2.",
	"containsPlace": "Location %1 contains %2."
}

show_limit = 5


var backgroundPage = undefined
main_handler = function() {
	backgroundPage.console.log('Popup script starting');
	var relations = backgroundPage.getRelations()
	var relation_prefab = $("#relation-prefab")
	var article_prefab = $("#article-prefab")
	relation_prefab.remove()
	article_prefab.remove()
	$('body').on('click', 'a', function(){
		chrome.tabs.create({url: $(this).attr('href'), active: false});
		return false;
	})
	$("#loadmore").click(function(){
		load_relations(relations, relation_prefab, article_prefab)
		$(".agree").click(voteHandler)
		$(".disagree").click(voteHandler)
		$(".done").click(function(event){
			article_header = $(event.target).parent().parent().parent().parent().parent()
			article = article_header.data("article")
			backgroundPage.removeRelations(article)
			current_index = 0
			$('[data-article="' + article + '"]').slideUp('slow', function(){$(this).remove()})
		})
		$('[data-ajaxload]').hover(function() {
			var element=$(this);
			element.off('mouseenter mouseleave');
			url = element.data('ajaxload')
			if (!url.includes("wikidata")){
				return
			}
			$.get(url, function(data) {
				console.log(data)
				text = data.entities[url.substring(url.lastIndexOf("/") + 1)].labels.en.value
				element.popover({content: text, placement: "top", trigger: "hover", container: "body"}).popover('show')
			});
		});
	})
	$("#loadmore").click()
	$('[data-toggle="popover"]').popover({container: 'body'});
}

var voteHandler = function(event){
	relation = $(event.target).parent().parent()
	id = relation.data("id")
	article = relation.data("article")
	type = $(event.target).hasClass("agree") ? "agree" : "disagree"
	relations = backgroundPage.getRelations()
	$.ajax("http://localhost:8080/relations/" + id + "/" + type, {
		method: "POST",
		success: function(data){
			relation.slideUp('slow', function(){relation.remove()})
			votedElement = relations[article].filter(function(element){return element.id == id}).shift()
			backgroundPage.removeRelation(article, votedElement)
		}
	})
}

current_index = {}
shown_articles = []
function load_relations(relations, relation_prefab, article_prefab){
	number_of_loaded = 0;
	number_of_articles_without_relations = 0
	Object.keys(relations).forEach(function(key) {
		if(number_of_loaded >= show_limit){
			return
		}
		if (relations[key].length == 0) {
			number_of_articles_without_relations ++
			return
		}
		if (shown_articles.indexOf(key) == -1){
			shown_articles.push(key)
			current_index[key] = 0
			var article_title = article_prefab.clone()
			article_title.find(".article").html("<h4>Article:</h4><p>" + key + "</p>")
			article_title.attr("data-article", key)
			article_title.insertBefore($("#loadmore").parent().parent())
		}
		for(i=current_index[key]; i<current_index[key]+show_limit && i<relations[key].length; i++){
			var relation_data = relations[key][i]
			var relation = relation_prefab.clone()
			relation.find("div > p").html(relation_sentence_map[relation_data.predicate]
				.replace("%1", '<a href="' + relation_data.subject + '" data-ajaxload="' + relation_data.subject + '">' + map_uri(relation_data.subject) + "</a>")
				.replace("%2", '<a href="' + relation_data.object + '" data-ajaxload="' + relation_data.object + '">' + map_uri(relation_data.object) + "</a>"))
			relation.attr("data-id", relation_data.id)
			relation.attr("data-article", key)
			relation.insertBefore($("#loadmore").parent().parent())
			number_of_loaded ++
			current_index[key] ++
			if(number_of_loaded >= show_limit){
				return
			}
		}
	});
	if (number_of_loaded == 0) {
		$("#loadmore").prop('disabled', true)
	}
	if(Object.keys(relations).length == number_of_articles_without_relations){
		if($(".article").length != 0){
			return
		}
		var article_title = article_prefab.clone()
		article_title.find(".article").html("<h4>No relations found</h4>")
		article_title.find(".done").hide()
		article_title.insertBefore($("#loadmore").parent().parent())
	}
}

function map_uri(uri){
	entity = uri.substring(uri.lastIndexOf("/") + 1)
	if(uri.includes("dbpedia")){
		return "DBPedia:" + entity
	}
	if(uri.includes("yago-knowledge")){
		return "Yago:" + entity
	}
	if(uri.includes("wikidata")){
		return "WikiData:" + entity
	}
	if(uri.includes("fer.hr")){
		return "FER:" + entity
	}
	return uri
}

chrome.runtime.getBackgroundPage(function(page){
	backgroundPage = page
	$(document).ready(main_handler);
})
