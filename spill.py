#!/usr/bin/env python
# -*- coding: utf-8 -*-

from filering import stoppwords
import json

class Spill:
    def __init__(self, json_data):
        self.marc = json_data
        self.spill = {}

    def __str__(self):
        return json.dumps(self.spill)


    def render_spill(self):
        self.f_245()
        self.f_008()
        self.f_leader()
        #self.year()

    def get_spill(self):
        self.render_spill()
        return self.__str__()

    def year(self):
        try:
            f_260_c = self.marc['260'][0]
        except Exception as e:
            print "year exception", e

        

    def f_245(self):
        print "in 245"
        try:
            ind1, ind2 = self.marc['245'][0:2]
            sfs = self.marc['245'][2]
            try:
                if sfs.get('a', None):
                    self.spill['240'] = {'a': "%s." % sfs['a'][0]}

            except:
                1
        except:
           1

    def f_008(self):
        print "in 008"
        try:
            sfs = self.marc['008']
            d = {}
            d['00_date_entered'] = sfs[0:6]
            d['06_type_of_date'] = sfs[6]
            d['07_date_1'] = sfs[7:11]
            d['11_date_2'] = sfs[11:15]
            d['15_place'] = sfs[15:18]
            d['18_illustrations'] = sfs[18:22]
            d['22_target_audience'] = sfs[22]
            d['23_form_of_item'] = sfs[23]
            d['24_nature_of_contents'] = sfs[24:28]
            d['28_government_publication'] = sfs[28]
            d['29_conference_publication'] = sfs[29]
            d['30_festschrift'] = sfs[30]
            d['31_index'] = sfs[31]
            d['32_undefined'] = sfs[32]
            d['33_literary_form'] = sfs[33]
            d['34_biography'] = sfs[34]
            d['35_language'] = sfs[35:38]
            d['38_modified_record'] = sfs[38]
            d['39_cataloging_source'] = sfs[39]

        except Exception as e:
            print "008 exception", e  
        self.spill['008'] = d

    def f_leader(self):
        print "in leader"
        try:
            ldr = self.marc['leader']
            d = {}
            d['00_record_length'] = ldr[0:5]
            d['05_record_status'] = ldr[5]
            d['06_type_of_record'] = ldr[6]
            d['07_bibliographic_level'] = ldr[7]
            d['08_type_of_control'] = ldr[8]
            d['09_character_coding_scheme'] = ldr[9]
            d['10_indicator_count'] = ldr[10]
            d['11_subfield_code_count'] = ldr[11]
            d['12_base_address_of_data'] = ldr[12:17]
            d['17_encoding_level'] = ldr[17]
            d['18_descriptive_cataloging_form'] = ldr[18]
            d['19_descriptive_cataloging_form'] = ldr[19]
            d['20_multipart_resource_record_level'] = ldr[20]
            d['21_length_of_the_starting_character_position_portion'] = ldr[21]
            d['22_length_of_the_implementation_defined_portion'] = ldr[22]
            d['23_undefined'] = ldr[23]
        except Exception as e:
            print "leader exception", e
        self.spill['leader'] = d
