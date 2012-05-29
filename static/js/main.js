//record
// - uid
// - marc
// - spill
$.fn.serializeObject = function() {
  var o = {};
  var fields = [];
  $.each($('#fields .control_field'), function() {
    var obj = {};
    var field_label = $(this).find('.field_label');
    obj[field_label.attr('name')] = field_label.val();
    fields.push(obj);
  });
  $.each($('#fields .regular_field'), function() {
    var field_name = $(this).find('.field_label').val();
    var ind1 = $(this).find('.ind1');
    var ind2 = $(this).find('.ind2');
    var subfields = $(this).find('.subfields').val();
    var r = /[a-z]‡/g;
    var subfield = {};
    var match = {};
    while(match = r.exec(subfields)) {
      subfield[match[0][0]] = subfields.substring(match.index + match[0].length, subfields.length);
    }

    var obj = {}
    obj[field_name] = {
      "ind1": $(this).find('.ind1').val(),
      "ind2": $(this).find('.ind2').val(),
      "subfields": [subfield], // TODO: split on separator
    };
    fields.push(obj);
  });
  o['fields'] = fields;
  o['leader'] = $(this).find("input[name='leader']").val();
  return o;
}

$(function() {
  this.collection = new Collection();
  this.router = new Router([this.collection]);

  this.router.on("route:record", function(data) {
    //this.collection.get(data).fetch();
  });

  this.collection.on('add', function(model) {
    var view = new View({model: model});
    view.render();
  });

  Backbone.history.start({pushState: true, root: "/"});

  // TODO: onunload:
  //if (ajaxInProgress)
  //  confirm('ajaxInProgress; break and leave?')

});

var Record = Backbone.Model.extend({
  urlRoot:'/record/bib',
  parse: function(response) {
    var fields = response['fields'];
    for (field in fields) {
      var key = _.keys(fields[field])[0];
      if(parseInt(key, 10) <= 8) { // We have a ControlField? Yes, that's the idea! :)
        fields[field].control_field = true;
      } else {
        fields[field].control_field = false;
      }
    }
    return {
      leader: response['leader'],
      fields: fields,
    };
  },
  save: function(attributes, options) {
    _.each(this.get('fields'), function(instance) { delete instance['control_field']; });
    Backbone.Model.prototype.save.call(this, attributes, options);
  },
});

var Collection = Backbone.Collection.extend({
  model: Record,
});

var Router = Backbone.Router.extend({
  initialize: function(options) {
    this.collection = options[0];
    self = this;
  },
  routes: {
    "record/bib/:bibid": "record"
  },
  record: function(bibid) {
    var record = new Record({id: bibid});
    record.fetch({
      success: function(model, response) {
        self.collection.add(model);
      },
    });
  },
});

var View = Backbone.View.extend({
  el: $('#fields'),
  leader_template: _.template($('#leader-template').html()),
  field_row_template: _.template($('#field-row-template').html()),
  control_row_template: _.template($('#control-row-template').html()),
  bib_autocomplete_template: _.template($('#bib-autocomplete-template').html()),

  events: {
    "click .subfields": "update_data" // TODO: perhaps consider other triggers..
  },

  update_data: function(event) {
    // TODO: save to model or perhaps to front-backend
  },

  render: function() {

    this.setupGlobalKeyBindings(this.model);

    $(this.el).html(this.leader_template({leader: this.model.get('leader')}));

    var control_fields = _.filter(this.model.get('fields'), function(field) {
      return field['control_field'] == true;
    });
    for (field in control_fields) {
      $(this.el).append(this.control_row_template({
        label: _.keys(control_fields[field])[0],
        value: _.values(control_fields[field])[0],
      }));
    }

    var fields = _.filter(this.model.get('fields'), function(field) {
      return field['control_field'] == false;
    });
    for (field in fields) {
      var key = _.keys(fields[field])[0];
      var value = _.values(fields[field])[0];
      $(this.el).append(this.field_row_template({
        label: key,
        ind1: value['ind1'],
        ind2: value['ind2'],
        subfields: value['subfields'],
      }));
    }

    this.setupBibAutocomplete();
    this.setupRecordKeyBindings();

  },

  setupGlobalKeyBindings: function (model) {
    $("input[name='publish']").on('click', function() {
      model.save();
    });
    $(document).jkey('ctrl+b',function(){
      model.save();
    });
  },

  setupRecordKeyBindings: function () {
    $('input', this.el).jkey('f3',function() {
        alert('Insert row before...');
    });
    $('input', this.el).jkey('f4',function() {
        alert('Insert row after...');
    });
    //$('input', this.el).jkey('f2',function() {
    //    alert('Show valid marc values...');
    //});
    //$(this.el).jkey('ctrl+t', function() {
    //  this.value += '‡'; // insert subkey delimiter
    //});
    // TODO: disable when autocompleting:
    //$('input', this.el).jkey('down',function() {
    //    alert('Move down');
    //});
  },

  setupBibAutocomplete: function () {
    var view = this;
    var suggestUrl = "/suggest/auth";
    $('.marc100 input.subfields'
      + ', .marc600 input.subfields'
      + ', .marc700 input.subfields', this.el).autocomplete(suggestUrl, {

        remoteDataType: 'json',
        autoWidth: "width",

        beforeUseConverter: function (repr) {
          return MARC.getSubFieldA(repr);
        },

        processData: function (results) {
          return results.map(function (item) {
            var value = view.authSuggestItemToFieldRepr(item);
            return {value: value, data: item};
          });
        },

        showResult: function (value, data) {
          return view.bib_autocomplete_template({value: value, data: data});
        },

        onItemSelect: function(item) {
          //console.log(item);
        }

    });
  },

  authSuggestItemToFieldRepr: function (item) {
    var f100 = item.marc['100'];
    return "a\u2021 "+ f100.a +",d\u2021 "+ f100.d;
  }

});

// TODO: merge with marcjson.js and marcmap.json
var MARC = {

  fieldExpr: new RegExp('\\w\u2021\\s*(.+?)((\\s*,?\\s*\\w\u2021)|$)'),

  /**
   * Expect:
   *  this.getSubFieldA("a‡ Jansson, Tove,d‡ 1914-2001")[1] == 'Jansson, Tove'
   *  this.getSubFieldA("a‡ Jansson, Tove")[1] == 'Jansson, Tove'
   *  this.getSubFieldA("Jansson, Tove")[1] == null
   */
  getSubFieldA: function (repr) {
    var parsed = repr.match(this.fieldExpr);
    return parsed? parsed[1] : repr;
  }

}
