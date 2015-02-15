$(function() {

var app = {};

// Routes.
app.Router = Backbone.Router.extend({
    routes: {
        "query/:query": "itemQuery",
    },
    itemQuery: function(query) {
        var queryURL = query.split(/\s+/).map(encodeURIComponent).join('/');
        $.getJSON('/query/' + queryURL, function(data) {
            var results = new app.Albums(data);
            app.appView.showAlbums(results);
        });
    }
});

// Model.
app.Art = Backbone.Model.extend({
    urlRoot: '/art',
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
    initialize: function(data) {
        var arts_data = _.map(data.art_files,
                          function(d) {
                            d['album_id'] = data.id;
                            return d;
                          });
        var arts = new app.Arts(arts_data);
        this.arts = arts;
    }
});
app.Albums = Backbone.Collection.extend({
    model: app.Album
});

// Album view
app.AlbumView = Backbone.View.extend({
    tagName: "div",
    attributes: {"class": "album"},
    template: _.template($('#album-template').html()),
/*    events: {
        'click': 'select',
    },*/
    initialize: function() {
    },
    render: function() {
        this.$el.html(this.template(this.model.toJSON()));
        var foo = this.$el;
        this.model.arts.each(function(art) {
            var view = new app.ArtView({model: art});
            foo.children(".arts").append(view.render().el);
        });
        this.$el.children(".arts").append("<div style='clear: both'/>");
        return this;
    },
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
        'click .artcontainer': 'artClick'
    },
    artClick: function(ev) {
        $('#artview img').attr('src', $(ev.target).css('background-image').slice(5, -2));
        $('#artview').css('display', 'block');
    }
});
// Main app view.
app.AppView = Backbone.View.extend({
    el: $('body'),
    events: {
        'submit #queryForm': 'querySubmit',
        'click #artview': 'closeArtView'
    },
    querySubmit: function(ev) {
        ev.preventDefault();
        app.router.navigate('query/' + escape($('#query').val()), true);
    },
    closeArtView: function(ev) {
        $('#artview').css('display', 'none');
    },
    initialize: function() {
        this.shownAlbums = null;
    },
    showAlbums: function(albums) {
        this.shownAlbums = albums;
        $('#content').empty();
        albums.each(function(album) {
            var view = new app.AlbumView({model: album});
            album.entryView = view;
            $('#content').append(view.render().el);
        });
    },
});
app.router = new app.Router();
app.appView = new app.AppView();

// App setup.
Backbone.history.start({pushState: false});
});