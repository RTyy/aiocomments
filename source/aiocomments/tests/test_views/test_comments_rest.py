"""Tests for Comment REST API."""


async def create_comment(cli, data):
    """Comment create method."""
    resp = await cli.put('/api/comment/', json=data)
    return await resp.json()

async def load_comment(cli, cid):
    """Load comment method."""
    resp = await cli.get('/api/comment/{id}/'.format(id=cid))
    return await resp.json()


async def test_create_comment(cli):
    """Test for comment creation handler."""
    # test non json request
    response = await cli.put('/api/comment/')
    resp = await response.json()
    assert response.status == 400
    assert 'error' in resp

    # test bad request
    response = await cli.put('/api/comment/', json={'test': 'test'})
    resp = await response.json()

    assert response.status == 400
    assert 'error' in resp
    assert 'data_errors' in resp
    assert 'user_id' in resp['data_errors']
    assert 'i_id' in resp['data_errors']
    # assert 'itype_id' in resp['data_errors']
    assert 'content' in resp['data_errors']
    assert 'test' in resp['data_errors']

    # test valid request
    # create comment for the instance type 1:
    req_data = {
        'user_id': 1,
        'i_id': 1,
        'itype_id': 1,
        'content': 'test create comment'
    }
    created = await create_comment(cli, req_data)
    assert set(['id', 'author_id', 'i_id', 'itype_id',
                'content', 'created', 'updated']) == set(created.keys())

    desired = req_data.copy()
    del desired['user_id']

    desired['author_id'] = req_data['user_id']
    desired['id'] = created['id']
    desired['created'] = created['created']
    desired['updated'] = created['updated']
    assert desired == created


async def test_insert_injection(cli):
    """Test for possible insert injection."""
    req_data = {
        'user_id': 1,
        'i_id': 1,
        'itype_id': 1,
        'content': 'test\'"; SELECT 1 FROM comment;'
    }
    created = await create_comment(cli, req_data)
    assert created['content'] == req_data['content']


async def test_get_comment(cli):
    """Test for comment loading."""
    # test get nonexistent comment
    resp = await cli.get('/api/comment/{id}/'.format(id=0))
    assert resp.status == 404

    # create a comment
    req_data = {
        'user_id': 2,
        'i_id': 2,
        'itype_id': 2,
        'content': 'test get comment'
    }
    created = await create_comment(cli, req_data)
    assert created['id'] is not None

    # test get saved comment
    resp = await cli.get('/api/comment/{id}/'.format(id=created['id']))
    loaded = await resp.json()
    assert created == loaded


async def test_update_comment(cli):
    """Test for comment updating."""
    req_data = {
        'user_id': 3,
        'i_id': 3,
        'itype_id': 3,
        'content': 'test update comment'
    }
    created = await create_comment(cli, req_data)
    loaded = await load_comment(cli, created['id'])

    assert created == loaded

    # test valid data
    upd_data = {
        'user_id': 3,
        'content': 'updated comment'
    }
    response = await cli.post('/api/comment/{id}/'
                              .format(id=created['id']), json=upd_data)
    assert response.status == 200
    updated = await response.json()

    desired = loaded.copy()
    assert not desired['updated'] == updated['updated']

    desired['content'] = upd_data['content']
    desired['updated'] = updated['updated']
    assert updated == desired

    loaded = await load_comment(cli, created['id'])
    assert loaded == updated

    # test invalid permission
    upd_data = {
        'user_id': 1,
        'content': 'invalid updated comment'
    }
    response = await cli.post('/api/comment/{id}/'
                              .format(id=created['id']), json=upd_data)
    assert response.status == 403

    resp = await response.json()
    assert 'error' in resp

async def test_delete_leaf_comment(cli):
    """Test for comment deleting."""
    req_data = {
        'user_id': 4,
        'i_id': 4,
        'itype_id': 4,
        'content': 'test delete comment'
    }
    created = await create_comment(cli, req_data)

    # test valid data
    del_data = {
        'user_id': 4,
    }
    response = await cli.delete('/api/comment/{id}/'
                                .format(id=created['id']), json=del_data)
    assert response.status == 200

    deleted = await response.json()
    assert deleted == {}

    # check if comment is deleted
    resp = await cli.get('/api/comment/{id}/'.format(id=created['id']))
    assert resp.status == 404

    # test delete nonexistent comment
    del_data = {
        'user_id': 4,
    }
    response = await cli.delete('/api/comment/{id}/'
                                .format(id=0), json=del_data)
    assert response.status == 404

    # test invalid request user
    # create comment again
    created = await create_comment(cli, req_data)
    del_data = {
        'user_id': 1,
    }
    response = await cli.delete('/api/comment/{id}/'
                                .format(id=created['id']), json=del_data)
    assert response.status == 403


async def test_delete_branch_comment(cli):
    """Test for comment branch deleting."""
    req_data = {
        'user_id': 4,
        'i_id': 4,
        'itype_id': 4,
        'content': 'branch comment'
    }
    branch = await create_comment(cli, req_data)

    req_data = {
        'user_id': 4,
        'i_id': branch['id'],
        'itype_id': 0,
        'content': 'leaf comment'
    }
    leaf = await create_comment(cli, req_data)

    # test invalid request to delete branch comment
    del_data = {
        'user_id': 4,
    }
    response = await cli.delete('/api/comment/{id}/'
                                .format(id=branch['id']), json=del_data)
    # you cant delete the branch with children comments
    assert response.status == 400

    # delete leaf comment tho we could delete "branch" later
    response = await cli.delete('/api/comment/{id}/'
                                .format(id=leaf['id']), json=del_data)
    assert response.status == 200

    # branch should be still in the db
    response = await cli.get('/api/comment/{id}/'
                             .format(id=branch['id']), json=del_data)
    assert response.status == 200

    # check if comment is deleted
    response = await cli.get('/api/comment/{id}/'.format(id=leaf['id']))
    assert response.status == 404

    # delete "branch" again
    response = await cli.delete('/api/comment/{id}/'
                                .format(id=branch['id']), json=del_data)
    assert response.status == 200

    # check if comment id deleted
    response = await cli.get('/api/comment/{id}/'.format(id=branch['id']))
    assert response.status == 404
