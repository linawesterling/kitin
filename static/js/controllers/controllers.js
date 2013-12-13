var kitin = angular.module('kitin.controllers', []);

kitin.controller('ModalCtrl', function($scope, $modal) {
  
  $scope.opts = {
    backdrop: true,
    keyboard: true,
    backdropClick: true,
    // template:  t, // OR: templateUrl: 'path/to/view.html',
    templateUrl: 'modal-edit-auth',
    controller: 'OpenModalCtrl',
    backdropFade: true,
    dialogFade:false,
    windowClass: 'wide'
  };

  $scope.open = function() {
    var i = $modal.open($scope.opts);
  };
});

kitin.controller('OpenModalCtrl', function($scope, $modal) {
  $scope.close = function() {
    $scope.$close();
  };
});

kitin.controller('IndexCtrl', function($scope, $http) {
  document.body.className = 'index';
  $scope.drafts = $http.get("/drafts").success(function(data) {
    $scope.drafts = data.drafts;
  });

  $scope['delete'] = function(type, id) {
    $http.post("/record" + "/" + type + "/" + id + "/draft/delete").success(function(data, status) {
      $scope.drafts = data.drafts;
    });
  };
});


kitin.controller('SearchFormCtrl', function($scope, $location, $routeParams) {
  var searchTypeIndex = {
    bib: {key: "bib", label: "Bibliografiskt material"},
    auth: {key: "auth", label: "Auktoriteter"}
  };
  $scope.searchTypes = [searchTypeIndex.bib, searchTypeIndex.auth];
  $scope.setSearchType = function (key) {
    $scope.searchType = searchTypeIndex[key];
  };
  $scope.placeholders = {
    bib: "Sök bland bibliografiskt material (på ISBN, titel, författare etc.)",
    auth: "Sök bland auktoriteter (personer, ämnen, verk etc.)"
  };
  $scope.search = function() {
    $location.url("/search/" + $scope.searchType.key + "?q="+encodeURIComponent($scope.q));
  };
  $scope.$on('$routeChangeSuccess', function () {
    $scope.setSearchType($routeParams.recType || "bib");
  });
});


kitin.controller('SearchCtrl', function($scope, $http, $location, $routeParams, definitions, searchService, searchUtil) {

  var recType = $routeParams.recType;

  $scope.recType = recType;

  definitions.typedefs.then(function(data) {
    $scope.typeDefs = data.types;
  });

  $scope.enums = {};

  definitions.enums.bibLevel.then(function(data) {
    $scope.enums.bibLevel = data;
  });

  definitions.enums.encLevel.then(function(data) {
    $scope.enums.encLevel = data;
  });

  var facetLabels = []; // TODO: localization
  facetLabels['about.@type'] = "Typer";
  facetLabels['about.dateOfPublication'] = "Datum";
  $scope.facetLabels = facetLabels;

  document.body.className = 'search';

  $scope.q = $routeParams.q;
  $scope.f = $routeParams.f;
  var url = "/search/" + recType + ".json?q=" + encodeURIComponent($scope.q);
  if ($scope.f !== undefined) {
    url += "&f=" + $scope.f;
  }

  $scope.search = function() {
    $location.url(url);
  };

  $scope.getLabel = function (term) {
    var dfn = $scope.typeDefs[term];
    if (!dfn) return term;
    return dfn['label_sv'] || term;
  };

  $scope.firstPerson = function (work) {
    var candidate = work.attributedTo || work.influencedBy;
    return _.isArray(candidate)? candidate[0] : candidate;
  };

  var prevFacetsStr = $routeParams.f || "";

  if (!$routeParams.q) {
    return;
  }

  $scope.loading = true;
  searchService.search(url).then(function(data) {
    $scope.facetGroups = searchUtil.makeLinkedFacetGroups(recType, data.facets, $scope.q, prevFacetsStr);
    $scope.crumbs = searchUtil.bakeCrumbs(recType, $scope.q, prevFacetsStr);
    $scope.result = data;
    if (data.hits == 1) {
        $location.url("/edit" + data.list[0].identifier);
        $location.replace();
    }
    $scope.hitCount = data.hits.toString();
    $scope.loading = false;
  });

});


kitin.controller('EditCtrl', function($scope, $http, $routeParams, $timeout, records, definitions, userData, editUtil, $log) {
  $scope.logger = $log;

  var recType = $routeParams.recType, recId = $routeParams.recId;
  var path = "/record/" + recType + "/" + recId;

  var isNew = (recId === 'new');
  var newType = $routeParams.type;

  $scope.recType = recType;

  document.body.className = isNew? 'edit new' : 'edit';

  // Fetch definitions
  // TODO: load cached aggregate, or lookup part on demand from backend?
  $scope.enums = {};
  definitions.enums.bibLevel.then(function(data) {
    $scope.enums.bibLevel = data;
  });
  definitions.enums.encLevel.then(function(data) {
    $scope.enums.encLevel = data;
  });
  definitions.enums.catForm.then(function(data) {
    $scope.enums.catForm = data;
  });
  definitions.relators.then(function(data) {
    $scope.relators = data;
  });
  //definitions.countries.then(function(data) {
  //  $scope.countrylist = data;
  //});
  ////definitions.nationalities.then(function(data) {
  ////  $scope.nationalitylist = data;
  ////});
  definitions.conceptSchemes.then(function(data) {
    $scope.conceptSchemes = data;
  });

  definitions.typedefs.then(function(data) {
    var typedefs = data.types;
    $scope.getTypeDef = function (obj) {
      if (typeof obj === "undefined")
        return;
      return typedefs[obj['@type']];
    };
    // TODO: merge with getLabel (defined in SearchCtrl)
    $scope.getTypeLabel = function (obj) {
      if (typeof obj === "undefined")
        return;
      var dfn = $scope.getTypeDef(obj);
      return (dfn)? dfn['label_sv'] : obj['@type'];
    };
  });

  $scope.isLinked = function (thing) {
    var id = thing['@id'];
    return id && id.substring(0, 2) !== '_:';
  };

  function addRecordViewsToScope(record, scope) {
    scope.personRoleMap = editUtil.getPersonRoleMap(record, scope.relators);
    scope.unifiedClassifications = editUtil.getUnifiedClassifications(record);
    // FIXME: this is just a view object - add/remove must operate on source and refresh this
    // (or else this must be converted back into source form before save)
    var defaultSchemes = ['sao', 'saogf'];
    scope.schemeContainer = new editUtil.SchemeContainer(record.about.instanceOf, defaultSchemes);
  }

  if (isNew) {
    $http.get('/record/bib/new?type' + newType).success(function(data) {
      var record = $scope.record = data;
      addRecordViewsToScope(record, $scope);
    });
  } else {
    records.get(recType, recId).then(function(data) {
      var record = $scope.record = data['recdata'];

      if (recType === 'bib') {
        editUtil.patchBibRecord(record);
        addRecordViewsToScope(record, $scope);
      }

      $scope.etag = data['etag'];
      $scope.userSigel = userData.userSigel;

      $http.get("/record/" + recType + "/" + recId + "/holdings").success(function(data) {
        var holdingEtags = {};
        var items = editUtil.patchHoldings(data.list);
        $scope.holdings = items;
        var myHoldings = _.filter(items, function(i) { return i['location'] == userData.userSigel; });
        if (myHoldings <= 0) {
          $http.get("/holding/bib/new").success(function(data, status, headers) {
            data.location = $scope.userSigel;
            $scope.holding = data;
            data._isNew = true; // TODO: don't do this when etag works
          });
        } else {
          $scope.holding = myHoldings[0];
        }
        items.forEach(function (item) {
          if (item['@id']) {
            $http.get("/holding/"+ item['@id'].split("/").slice(-2)[1]).success(function (data, status, headers) {
              holdingEtags[data['@id']] = headers('etag');
            });
          }
        });
        $scope.holdingEtags = holdingEtags;
      });

    });
  }

  $scope.modifications = {saved: true, published: true};

  function onSaveState() {
    $scope.modifications.saved = true;
    $scope.modifications.lastSaved = new Date();
  }
  function onPublishState() {
    $scope.modifications.saved = true;
    $scope.modifications.published = true;
    $scope.modifications.lastPublished = new Date();
  }

  $scope.triggerModified = function () {
    $scope.modifications.saved = false;
    $scope.modifications.published = false;
  };

  $scope.modifiedClasses = function () {
    var classes = [], mods = $scope.modifications;
    if (mods.saved) classes.push('saved');
    if (mods.published) classes.push('published');
    return classes;
  };

  $scope.lastSavedLabel = function (tplt) {
    if (!$scope.modifications.lastSaved)
      return "";
    return tplt.replace(/%s/, $scope.modifications.lastSaved.toLocaleString());
  };

  $scope.lastPublishedLabel = function (tplt) {
    if (!$scope.modifications.lastPublished)
      return "";
    return tplt.replace(/%s/, $scope.modifications.lastPublished.toLocaleString());
  };

  $scope.promptConfirmDelete = function($event, type, id) {
    $scope.confirmDeleteDraft = {
      execute: function() {
        $http.post("/record" + "/" + type + "/" + id + "/draft/delete").success(function(data, status) {
          $scope.draft = null;
          $scope.confirmDeleteDraft = null;
        });
      },
      abort: function() {
        $scope.confirmDeleteDraft = null;
      }
    };
    $timeout(function() {
      openPrompt($event, "#confirmDeleteDraftDialog");
    });
  };

  if (isNew) {
    $scope.save = function() {
      records.create(recType, $scope.record).then(function(data) {
        $location.url('/edit/bib/' + data['document_id']);
      });
    };
  } else
  $scope.save = function() {
    var ifMatchHeader = $scope.etag.replace(/["']/g, "");
    records.save(recType, recId, $scope.record, ifMatchHeader).then(function(data) {
      $scope.record = data['recdata'];
      $scope.etag = data['etag'];
            onPublishState();
    });
  };

  $scope.saveDraft = function() {
    $http.post("/record/"+ $routeParams.recType +"/"+ $routeParams.recId +"/draft",
      $scope.record,
      {headers: {"If-match":$scope.etag}}
    ).success(function(data, status) {
      $scope.draft = data;
      $scope.draft.type = data['@id'].split("/").slice(-2)[0];
      $scope.draft.id = data['@id'].split("/").slice(-2)[1];
      onSaveState();
      //$('.flash_message').text("Utkast sparat!");
    });
  };

  $http.get("/draft/"+recType+"/"+recId).success(function(data, status, headers) {
    $scope.draft = data;
    $scope.draft.type = data['@id'].split("/").slice(-2)[0];
    $scope.draft.id = data['@id'].split("/").slice(-2)[1];
    $scope.etag = headers('etag');
  }).error(function(data, status) {
    //console.log(status);
  });

  $scope.newObject = function(subj, rel, type) {
    var obj = subj[rel] = editUtil.createObject(type);
  };

  $scope.addObject = function(subj, rel, type) {
    var collection = subj[rel];
    if (typeof collection === 'undefined') {
      collection = subj[rel] = [];
    }
    var obj = editUtil.createObject(type);
    collection.push(obj);
  };

  $scope.addObject = function(subj, rel, type, target) {
    var collection = subj[rel];
    if (typeof collection === 'undefined') {
      collection = subj[rel] = [];
    }
    var obj = editUtil.createObject(type);
    collection.push(obj);
    // Focus on added row
    if (target) {
      var $dataTable = angular.element('[data-ng-target='+target+']');
      $timeout(function() {
        $dataTable.find('tbody tr:last input:first').focus();
      });
    }
  };

  $scope.removeObject = function(subj, rel, index) {
    var obj = subj[rel];
    var removed = null;
    if (_.isArray(obj)) {
      removed = obj.splice(index,1)[0];
    } else {
      removed = subj[rel];
      subj[rel] = null;
    }
    if (typeof subj.onRemove === 'function') {
      subj.onRemove(rel, removed, index);
    }
    $scope.triggerModified();
  };

  $scope.addHolding = function(holdings) {
    holdings.push({shelvingControlNumber: "", location: constants['user_sigel']});
  };

  $scope.saveHolding = function(holding) {
    var etag = $scope.holdingEtags[holding['@id']];
    holding['annotates'] = { '@id': "/"+recType+"/"+recId };
    // TODO: only use etag (but it's not present yet..)
    if(!holding._isNew && (etag || holding.location === $scope.userSigel)) {
      $http.put("/holding/" + holding['@id'].split("/").slice(-2)[1], holding, {headers: {"If-match":etag}}).success(function(data, status, headers) {
        $scope.holdingEtags[data['@id']] = headers('etag');
      }).error(function(data, status, headers) {
        console.log("ohh crap!");
      });
    } else {
      if (holding._isNew) { delete holding._isNew; }
      console.log("we wants to post a new holding");
      $http.post("/holding", holding).success(function(data, status, headers) {
        $scope.holdingEtags[data['@id']] = headers('etag');
      }).error(function(data, status, headers) {
        console.log("ohh crap!");
      });
    }
  };

  $scope.deleteHolding = function(holdingId) {
    $http['delete']("/holding/" + holdingId).success(function(data, success) {
      console.log("great success!");
      $http.get("/record/" + recType + "/" + recId + "/holdings").success(function(data) {
        $scope.holdings = patchHoldings(data.list);
      });
    }).error(function() {
      console.log("oh crap!");
    });
  };

  var typeCycle = ['Book', 'EBook', 'Audiobook', 'Serial', 'ESerial'], typeIndex = 0;
  $scope.cycleType = function (evt, obj) {
    if (!obj || !evt.altKey) return;
    if (typeIndex++ >= typeCycle.length - 1) typeIndex = 0;
    obj['@type'] = typeCycle[typeIndex];
  };

  $scope.toJsonLdLink = function (id) {
    return id.replace(/^\/(resource\/)?/, '/jsonld/');
  };


  $scope.jsonLdKeys = function(obj) {
    if (angular.isArray(obj))
      return _.keys(obj);
    var result = [];
    for (var key in obj) {
      if (obj.hasOwnProperty(key) && key[0] !== '$') {
        result.push({key: key, value: obj[key]});
      }
    }
    result.sort(function (one, other) {
      var a1 = jsonLdObjectWeight(one.value),
          a2 = jsonLdObjectWeight(other.value);
      if (a1 === a2 && _.isObject(one.value)) {
        a1 = _.size(one.value);
        a2 = _.size(other.value);
      }
      var b1 = one.key,
          b2 = other.key;
      return 2 * (a1 > a2 ? 1 : a1 < a2 ? -1 : 0) +
        1 * (b1 > b2 ? 1 : b1 < b2 ? -1 : 0);
    });
    return _.collect(result, 'key');
  };

  function jsonLdObjectWeight(o) {
    if (_.isArray(o)) {
      return 3;
    } else if (_.isObject(o)) {
      if (!_.isUndefined(o['@id']))
        return 2;
      else
        return 1;
    } else {
      return 0;
    }
  }

});
