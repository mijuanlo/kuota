#!/usr/bin/env python3

import subprocess as sp
import os
import re
from functools import reduce
import time
import signal
import logging

HEAVY_SYSTEM_LIMIT = 0.3
GRACE_MEBIBYTES = 0.2
NEED_AVAILABLE_GIBIBYTES_ADMINS = 0.5
NEED_AVAILABLE_GIBIBYTES = HEAVY_SYSTEM_LIMIT + GRACE_MEBIBYTES

GROUP_DOMAIN_USERS_NAME = 'Domain Users'
GROUP_TEACHERS_NAME = 'teachers'
GROUP_STUDENT_NAME = 'students'

QUOTAS_FS = '/'
USERHOMES_FOLDER = '/home'

SLEEP_TIME = 10

logging.basicConfig(
    level = logging.DEBUG,
    format = '%(asctime)s %(message)s',
    handlers = [ logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

cache = {}

def execute(_command):
    _command = list(map(str, _command))
    try:
        _env = {
            'LANG': 'C',
            'LC_ALL': 'C',
            'LANGUAGE': 'C'
            }
        str_command = ' '.join(_command)
        if str_command not in cache:
            cached = {'time': 0,'output': None}
            cache.setdefault(str_command,{'time': 0,'output': None})
        else:
            cached = cache.get(str_command)
        if cached.get('time') > time.time() - SLEEP_TIME:
            logger.debug(f'Cached result for execution of {" ".join(_command)}')
            return cache.get(str_command).get('output')
        else:
            logger.debug(f'Executing {" ".join(_command)}')
            out = sp.check_output(_command,env=_env).decode()
            cache[str_command] = { 'time': time.time(), 'output': out }
        return out 
    except Exception as e:
        raise(e)

def get_repquota(_type):
    if _type not in ['u','g']:
        raise Exception('Type error')

    _skip_first_n_lines = 1
    _command = []
    _bin = ['/usr/sbin/repquota']
    _options = ['-O','csv',f'-{_type}']
    _fs = [QUOTAS_FS]
    
    _command.extend(_bin)
    _command.extend(_options)
    _command.extend(_fs)
    
    out = execute(_command)
    if _skip_first_n_lines:
        out = out.split('\n')[_skip_first_n_lines:]
    
    ret = {}
    for line in out:
        if line:
            User,BlockStatus,FileStatus,BlockUsed,BlockSoftLimit,BlockHardLimit,BlockGrace,FileUsed,FileSoftLimit,FileHardLimit,FileGraceline = line.split(',')
            ret[User] = { 'status': False if BlockStatus == 'ok' else True, 'used': int(BlockUsed), 'limit': int(BlockHardLimit) } 
    return ret

def get_all_repquota():
    return { 'user': get_repquota('u'), 'group': get_repquota('g') }

def get_all_groups():
    return list(get_repquota('g').keys())

def get_all_users():
    return list(get_repquota('u').keys())

def get_df():
    _skip_first_n_lines = 1
    _command = []
    _bin = ['/usr/bin/df']
    _options = ['--output=used,avail']
    _fs = [QUOTAS_FS]

    _command.extend(_bin)
    _command.extend(_options)
    _command.extend(_fs)
    
    out = execute(_command)
    
    if _skip_first_n_lines:
        out = out.split('\n')[_skip_first_n_lines:]
    
    if len(out) > 0 and out[0]:
        out = out[0].split()
        return {'used': int(out[0]), 'avail': int(out[1])}
    else:
        raise Exception(f'{out} is a unknown value')

    return out

def get_user_data(user):
    if not user:
        raise Exception('Invalid user for check info')
    
    if not isinstance(user,str):
        raise Exception('User must be a string')

    _command = []
    _bin = ['/usr/bin/id']
    
    _command.extend(_bin)
    _command.extend([user])

    try:
        out = execute(_command)
        result = re.search(r'^uid=(\d+)\(([^\)]+)\) gid=(\d+)\(([^\)]+)\) groups=(.*)$',out)
        ret = { 'user': { 'uid': None, 'name': None }, 'group': { 'gid': None, 'gname': None }, 'others': [] }
        if result:
            groups = [ gr for gr in list(result.groups()) if gr ]
            if len(groups) == 5:
                ret['user']['uid'] = int(groups[0])
                ret['user']['name'] = groups[1]
                ret['group']['gid'] = int(groups[2])
                ret['group']['gname'] = groups[3]
            else:
                raise Exception('Error parsing id information')
            groups = groups[4].split(',')
            for i in range(len(groups)):
                m = re.search(r'^(\d+)\(([^)]+)\)$',groups[i])
                if m:
                    others_gid,others_gname = m.groups()
                    ret['others'].append({'gid': others_gid, 'gname': others_gname})
            return ret
    except Exception as e:
        raise Exception(f"Fail getting user data {' '.join(_command)}, error is: {e}")


def get_users_groups():
    _path = USERHOMES_FOLDER
    userdata = {}
    for _username in os.listdir(_path):
        _fullpath = os.path.join(_path,_username)
        if os.path.isdir(_fullpath):
            userdata.setdefault(_username,get_user_data(_username))
    return userdata

def get_domain_users():
    userlist = {}
    _data = get_users_groups()
    for us in _data.keys():
        _all_groups = {}
        _all_groups.setdefault(_data.get(us).get('user').get('name'),None)
        _all_groups.setdefault(_data.get(us).get('group').get('gname'),None)
        for oth in _data.get(us).get('others'):
            _all_groups.setdefault(oth.get('gname'),None)
        _all_groups = _all_groups.keys()
        for _type in [GROUP_DOMAIN_USERS_NAME, GROUP_TEACHERS_NAME, GROUP_STUDENT_NAME]:
            userlist.setdefault(_type,[])
            if _type in _all_groups:
                userlist[_type].append(us)
    return userlist

def calculate_sizes():
    repquota_data = get_all_repquota()
    df_data = get_df()

    ret = {}
    ret['need_available'] = int( NEED_AVAILABLE_GIBIBYTES * 1024 * 1024 )
    ret['need_available_admins'] = int( NEED_AVAILABLE_GIBIBYTES_ADMINS * 1024 * 1024 )
    ret['size_local_groups'] = reduce(lambda a,b: a+b , ( groupdata.get('used') for groupname,groupdata in repquota_data.get('group').items() if groupname != GROUP_DOMAIN_USERS_NAME))
    ret['size_domain'] = repquota_data.get('group').get(GROUP_DOMAIN_USERS_NAME).get('used')
    ret['total_usable_fs'] = df_data.get('used') + df_data.get('avail')
    ret['fs_available'] = df_data.get('avail')
    ret['fs_heavy_limit'] = HEAVY_SYSTEM_LIMIT * 1024 * 1024
    ret['quota_domains'] = int(ret['total_usable_fs'] - ret['size_local_groups'] - ret['need_available'])
    ret['current_available_domain_users_remaning'] = int(ret['quota_domains'] - ret['size_domain'] - ret['need_available_admins'] )
    
    return ret

def apply_quota(target, value, _type):
    if _type not in ['u','g']:
        raise Exception('Need valid _type')
    if _type == 'u':
        if target not in get_all_users():
            raise Exception('Invalid user')
    else:
        if target not in get_all_groups():
            raise Exception('Invalid group')
    if not isinstance(value,(int,float)):
        raise Exception('Need valid quota value')
    
    value = int(value)

    _command = []
    _bin = ['/usr/sbin/setquota']
    _options = [f'-{_type}']
    _target = [target]
    _fs = [QUOTAS_FS]

    _quota = [ value , value , 0 , 0 ]

    _command.extend(_bin)
    _command.extend(_options)
    _command.extend(_target)
    _command.extend(_quota)
    _command.extend(_fs)

    out = execute(_command)
    return out

def apply_quota_group(group, value):
    apply_quota(group, value, _type='g')

def apply_quota_user(user, value):
    apply_quota(user, value, _type='u')

def apply_calculated_quota_group():
    current_quota = get_repquota('g').get(GROUP_DOMAIN_USERS_NAME).get('limit')
    quota_domains = calculate_sizes().get('quota_domains')
    if current_quota != quota_domains:
        apply_quota_group(GROUP_DOMAIN_USERS_NAME, quota_domains )

def apply_calculated_quota_users():
    grace_mebibyte = 5 * 1024
    sizes = calculate_sizes()
    users = get_domain_users()
    repquota_data = get_repquota('u')
    privileged = users.get(GROUP_TEACHERS_NAME) + users.get(GROUP_STUDENT_NAME)
    non_privileged = [ us for us in users.get(GROUP_DOMAIN_USERS_NAME) if us not in privileged ]
    if sizes.get('current_available_domain_users_remaning') < 0:
        if sizes.get('fs_available') < sizes.get('fs_heavy_limit'):
            for us in non_privileged:
                current_quota_limit = repquota_data.get(us).get('limit')
                current_quota_used = repquota_data.get(us).get('used')
                if current_quota_limit != current_quota_used:
                    apply_quota_user(us, current_quota_used)
            for us in privileged:
                current_quota_limit = repquota_data.get(us).get('limit')
                current_quota_used = repquota_data.get(us).get('used')
                if current_quota_limit != current_quota_used + grace_mebibyte:
                    apply_quota_user(us, current_quota_used + grace_mebibyte)
        else:
            for us in non_privileged:
                current_quota_limit = repquota_data.get(us).get('limit')
                current_quota_used = repquota_data.get(us).get('used')
                if current_quota_limit != current_quota_used + grace_mebibyte:
                    apply_quota_user(us, current_quota_used + grace_mebibyte)

def get_exausted_quota(target, _type):
    if _type not in ['u','g']:
        raise Exception('Invalid _type')
    
    if _type == 'u':
        _data = get_repquota('u')
    else:
        _data = get_repquota('g')
    
    if target:
        if target not in _data.keys():
            raise Exception('Invalid target')
        return _data.get(target).get('status')
    else:
        return [ _target for _target,_target_data in _data.items() if _target_data.get('status') ]

def get_exausted_quota_groups():
    return get_exausted_quota(None,'g')

def get_exausted_quota_users():
    return get_exausted_quota(None,'u')

def reset_quota(target, _type):
    if _type not in ['u','g']:
        raise Exception('Invalid type')
    if _type == 'u':
        _data = get_repquota('u')
    else:
        _data = get_repquota('g')
    if target:
        if target not in _data.keys():
            raise Exception('Invalid target')
        if _data.get(target).get('limit') != 0:
            apply_quota(target,0,_type)
    else:
        for target in ( key for key in _data.keys() if _data.get(key).get('limit') != 0 ) :
            apply_quota(target,0,_type)

def reset_all_quotas():
    reset_quota(None,'u')
    reset_quota(None,'g')

RUN = True
def take_care_system():
    global RUN
    _tik = 0.1
    logger.info('Starting quota manager')
    while RUN:
        logger.debug('Monitoring space and applying quotas if needed')
        _sleep_time = float(SLEEP_TIME)
        apply_calculated_quota_group()
        apply_calculated_quota_users()
        while _sleep_time > 0 and RUN:
            time.sleep(_tik)
            _sleep_time = _sleep_time - _tik
    reset_all_quotas()

def exit_service(*args,**kwargs):
    global RUN
    logger.debug('Exitting quota manager')
    RUN = False

if __name__ == '__main__':
        signal.signal(signal.SIGINT, exit_service)
        take_care_system()
        # print(get_all_repquota())
        # print(get_df())
        # print(get_domain_users())
        # print(calculate_sizes())
        # print(apply_calculated_quota_group())
        # print(apply_calculated_quota_users())
        # print(get_exausted_quota_groups())
        # print(get_exausted_quota_users())
        # print(reset_all_quotas())





