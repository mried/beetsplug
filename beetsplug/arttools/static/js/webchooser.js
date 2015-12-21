$(function() {

var app = {};

// ====================== Router ======================

app.Router = Backbone.Router.extend({
    routes: {
        "": "itemQuery",
        "query/(:query)": "itemQuery"
    },
    itemQuery: function(query) {
        if(!query) {
            query = "";
        }
        var queryURL = query.split(/\s+/).map(encodeURIComponent).join('/');
        $.getJSON('/query/' + queryURL, function(data) {
            var results = new app.Albums(data);
            app.appView.showAlbums(results);
        });
    }
});

// ====================== Models ======================

app.Art = Backbone.Model.extend({
    urlRoot: '/art',
    idAttribute: 'file_name',
    isBadSize: function() {
        return this.get('width') < size_thresh || this.get('height') < size_thresh;
    },
    isBadAspectRatio: function() {
        return this.get('aspect_ratio') < ar_thresh;
    },
    isBadArt: function() {
        return this.isBadSize() || this.isBadAspectRatio();
    }
});

app.Arts = Backbone.Collection.extend({
    urlRoot: '/arts',
    model: app.Art
});

app.Album = Backbone.Model.extend({
    urlRoot: '/album',
    idAttribute: 'id',
    initialize: function(data) {
        this.parse(data);
    },
    parse: function(data) {
        var album = this;
        var arts_data = _.map(data.art_files,
                          function(d) {
                            d['album'] = album;
                            return d;
                          });
        this.arts = new app.Arts(arts_data);

        return data;
    }
});

app.Albums = Backbone.Collection.extend({
    url: '/query/',
    model: app.Album
});

// ====================== Views ======================

app.AlbumView = Backbone.View.extend({
    tagName: "div",
    attributes: function() {
        var classes = "album";
        if(this.model.arts.length == 1) {
            classes += " oneArt";
        }
        return {"class": classes}
    },
    template: _.template($('#album-template').html()),
    events: {
        'click .collect-art': 'collectArt',
        'dragleave': 'onDragLeave',
        'drop': 'onDragDrop',
        'dragover': 'onDragOver'
    },
    onDragLeave: function (e) {
        this.$('div.art-drag-hover').hide();
    },
    onDragDrop: function (e) {
        e.preventDefault();

        this.$('div.art-drag-hover').hide();

        var formData = new FormData();
        for (var i = 0; i < e.originalEvent.dataTransfer.files.length; i++) {
            if (e.originalEvent.dataTransfer.items[i].type.slice(0, 5) == "image") {
                formData.append('file', e.originalEvent.dataTransfer.files[i]);
            }
        }

        if (formData.length == 0) {
            return;
        }

        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/uploadArt');
        xhr.onload = function () {
            if (xhr.status === 200) {
                console.log('all done: ' + xhr.status);
            } else {
                console.log('Something went terribly wrong...');
            }
        };

        xhr.send(formData);
    },
    onDragOver: function (e) {
        e.preventDefault();
        for (var i = 0; i < e.originalEvent.dataTransfer.types.length; ++i) {
            if (e.originalEvent.dataTransfer.items[i].type.slice(0, 5) == "image") {
                this.$('div.art-drag-hover').show();
                e.originalEvent.dataTransfer.dropEffect = "copy";
                return false;
            }
        }
        e.originalEvent.dataTransfer.dropEffect = "none";

        return true;
    },
    initialize: function() {
        this.listenTo(this.model, 'change', this.render);
        this.listenTo(this.model, 'reset', this.render);
        this.listenTo(this.model, 'sync', this.render);
        _.bindAll(this, 'renderArt');
    },
    render: function() {
        this.$el.html(this.template(this.model.toJSON()));
        this.model.arts.forEach(this.renderArt);
        this.$el.children(".arts").append("<div style='clear: both'></div>");

        if(this.model.get('collecting')) {
            var model = this.model;
            setTimeout(function() { model.fetch(); }, 1000);
        }

        return this;
    },
    renderArt: function(art) {
        var artView = new app.ArtView({model: art});
        this.$('div.arts').append(artView.render().el);
    },
    collectArt: function() {
        var model = this.model;
        $.getJSON('/collectArt/' + model.get('id'), function() {
            model.fetch();
        });
    }
});

// Art view
app.ArtView = Backbone.View.extend({
    tagName: "div",
    attributes: {"class": "art"},
    template: _.template($('#art-template').html()),
    render: function() {
        this.$el.html(this.template(this.model.toJSON()));
        this.$el.addClass(this.model.isBadArt() ? 'badArt' : 'goodArt');
        return this;
    },
    events: {
        'click .artcontainer': 'artClick',
        'click .art-remove': 'artRemove',
        'click .art-choose': 'artChoose'
    },
    artClick: function() {
        var album = this.model.get('album');
        var imageUrl = '/art/' + album.get('id') + '/' + this.model.get('file_name');
        var artview = $('#artview');
        artview.find('img').attr('src', imageUrl);
        artview.css('display', 'block');
    },
    artRemove: function() {
        var album = this.model.get('album');
        $.getJSON('/deleteArt/' + album.get('id') + '/' + this.model.get('file_name'), function() {
            album.fetch();
        });
    },
    artChoose: function() {
        var album = this.model.get('album');
        $.getJSON('/chooseArt/' + album.get('id') + '/' + this.model.get('file_name'), function() {
            album.fetch();
        });
    }
});

// Main app view.
app.AppView = Backbone.View.extend({
    el: $('body'),
    events: {
        'submit #queryForm': 'querySubmit',
        'click #artview': 'closeArtView',
        'click #checkHideOneArt': 'toggleHideOneArt',
        'click #checkHideBadArt': 'toggleHideBadArt',
        'click #checkHideGoodArt': 'toggleHideGoodArt',
        'click #accept-all': 'acceptAll',
        'click #collect-all': 'collectAll'
    },
    querySubmit: function(ev) {
        ev.preventDefault();
        var query = this.getQuery();
        app.router.navigate('query/' + encodeURI(query), {trigger: true});
    },
    closeArtView: function() {
        $('#artview').css('display', 'none');
    },
    initialize: function() {
    },
    toggleHideOneArt: function () {
        $('#content').toggleClass('hideOneArt');
    },
    toggleHideBadArt: function () {
        $('#content').toggleClass('hideBadArt');
    },
    toggleHideGoodArt: function () {
        $('#content').toggleClass('hideGoodArt');
    },
    getQuery: function () {
        return $('#query').val();
    },
    getQueryUrl: function () {
        var query = $('#query').val();
        if(!query) {
            query = "";
        }
        return query.split(/\s+/).map(encodeURIComponent).join('/');
    },
    acceptAll: function () {
        var query = $('#query').val();
        $.getJSON('/acceptArtQuery/' + this.getQueryUrl(), function() {
            app.router.navigate('query/' + encodeURI(query), {trigger: true});
        });
    },
    collectAll: function () {
        var query = $('#query').val();
        $.getJSON('/collectArtQuery/' + this.getQueryUrl(), function() {
            app.router.navigate('query/' + encodeURI(query), {trigger: true});
        });
    },
    showAlbums: function(albums) {
        $('#content').empty();
        albums.each(function(album) {
            var view = new app.AlbumView({model: album});
            album.entryView = view;
            $('#content').append(view.render().el);
        });
    }
});
app.router = new app.Router();
app.appView = new app.AppView();

// App setup.
Backbone.history.start({pushState: false});
});